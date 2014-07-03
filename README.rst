OSProfiler
==========

OSProfiler is an OpenStack cross-project profiling library.


Background
----------

OpenStack consists of multiple projects. Each project, in turn, has multiple
services. To process some request, e.g. to boot a virtual machine, OpenStack
uses multiple services from different projects. In case something works too
slowly, it's extremely complicated to understand what exactly goes wrong and to
locate the bottleneck.

To resolve this issue, we introduce a tiny but powerful library,
**osprofiler**, that is going to be used by all OpenStack projects and their
python clients. To be able to generate 1 trace per request, that goes through
all services invoved, and builds a tree of calls (see an
`example <http://pavlovic.me/rally/profiler/>`_).


Why not cProfile and etc?
-------------------------

**The scope of this lib is a quite different:**

* We are interested in getting one trace of points from different service,
  not tracing all python calls inside one process

* This library should be easy integrable in OpenStack. It means that:

  * It shouldn't require too much changes in code bases of projects

  * We should be able to turn it off fully

  * We should be able to keep it turned on in lazy mode (trace on request)


OSprofiler API version 0.2.0
----------------------------

There are couple of things that you should know about API before learning it.

* **3 ways to add new trace point**

    .. parsed-literal::

        from osprofiler import profiler

        def some_func():
            profiler.start("point_name", {"any_info_about_point": "in_this_dict"})
            # your code
            profiler.stop({"any_info_about_point": "in_this_dict"})


        @profiler.Trace("point_name", {"any_info_about_point": "in_this_dict"})
        def some_func2():
            pass

        def some_func3():
            with profiler.trace("point_name", {"any_info_about_point": "in_this_dict"}):
                # some code here

* **How works profiler actually?**

  * **@profiler.Trace()** and **profiler.trace()** are just syntax sugar,
    that just call profiler.start() & profiler.stop() methods.

  * It sends to **collector** 1 message per every call of profiler.start()
    & profiler.stop(). So every trace points crates 2 records in collector.
    *(more about collector later)*

  * Trace points support nesting, so next sample will work properly:

      .. parsed-literal::

          profiler.start("parent_point")
          profiler.start("child_point")
          profiler.stop()
          profiler.stop()

      In sample above, we will create 2 points:

      This is implemented in quite simple manner. We have one stack that
      contains ids of all trace points. E.g.:

      .. parsed-literal::

          profiler.start("parent_point") # trace_stack.push(<new_uuid>)
                                         # send to collector -> trace_stack[-2:]

          profiler.start("parent_point") # trace_stack.push(<new_uuid>)
                                         # send to collector -> trace_stack[-2:]
          profiler.stop()                # send to collector -> trace_stack[-2:]
                                         # trace_stack.pop()

          profiler.stop()                # send to collector -> trace_stack[-2:]
                                         # trace_stack.pop()

      So with this information from collector, we can restore order and nesting
      of all points.

* **What is actually send to to collector?**

  Trace points are presented in collector as 2 messages (start and stop)

  .. parsed-literal::
    {
        "name": <point_name>-(start|stop)
        "base_id": <uuid>,
        "parent_id": <uuid>,
        "trace_id": <uuid>,
        "info": <dict>
    }

   * base_id - is <uuid> that is equal for all trace points that belongs
               to one trace, it is done to simplify process of retrieving
               all trace points related to one trace from collector
   * parent_id - is <uuid> that has parent trace point
   * trace_id - is <uuid> of current trace point
   * info - it's dictionary that contains user information passed via calls of
            profiler start & stop methods.



* **Setting up Collector.**

    Profiler doesn't include any collector for trace points, end user should
    provide method that will send message to collector. Let's take a look at
    trivial sample, where collector is just a file:

    .. parsed-literal::

        import json

        from osprofiler import notifier

        def send_info_to_file_collector(info, context=None):
            with open("traces", "a") as f:
                f.write(json.dumps())

        notifier.set(send_info_to_file_collector)

    So now on every **profiler.start()** and **profiler.stop()** call we will
    write info about trace point to the end of  **traces** file.


* **Initialization of profiler.**

    If profiler is not initialized, all calls of profiler.start() and
    profiler.stop() are ignored.

    Initialization is quite simple.

    .. parsed-literal::

        from osprofiler import profiler

        profiler.init("SECRET_HMAC_KEY", base_id=<uuid>, parent_id=<uuid>)

    "SECRET_HMAC_KEY" - will be discussed later, cause it's related to the
    integration of OSprofiler & OpenStack.

    **base_id** and **trace_id** will actually initialize trace_stack in
    profiler, e.g. stack_trace = [base_id, trace_id].



Integration with OpenStack
--------------------------

There are 4 topics related to integration OSprofiler & OpenStack:

* **What to use as centralized collector**

  We decided to use Ceilometer, because:

  * It's already integrated in OpenStack, so it's quite simple to send
    notifications to it from every project.

  * There is a OpenStack API in Ceilometer that allows us to retrieve all
    messages related to one trace. Take a look at
    *osprofiler.parsers.ceilometer:get_notifications*


* **How to setup profiler notifier, to send messages to this collector**

  We decided to use olso.messaging Notifier API, because:

  * oslo.messaging is integrated in all projects

  * It's the simplest way to send notification to Ceilometer, take a look at:
    *osprofiler.notifiers.messaging.Messaging:notify* method

  * We don't need to add any new CONF options in projects


* **How to initialize profiler, to have one trace cross all services**

    To enable cross service profiling we actually need to do send from caller
    to callee (base_id & trace_id). So callee will be able to init his profiler
    with these values.

    In case of OpenStack there are 2 kinds interaction between to services:

    * REST API

        It's well know that there are python clients for every projects,
        that generates proper HTTP request, and parses response to objects.

        These python clients are used in 2 cases:

        * User access OpenStack

        * Service from Project 1 would like to access Service from Project 2


        So what we need is to:

        * Put in python clients headers with trace info (if profiler is inited)

        * Add OSprofiler WSGI middleware to service, that will init profiler, if
          there are special trace headers.

        Actually the algorithm is a bit more complex. Python client are signed
        trace info, and WSGI middleware checks that it's signed with HMAC that
        is specified in api-paste.ini. So only user that knows HMAC key in
        api-paste.ini can init properly profiler and send trace info that will
        be actually processed.


    * RPC API

        RPC calls are used for interaction between services of one project. As
        we all known for RPC projects are using oslo.messaging. So the best way
        to enable cross service tracing (inside on project). Is to add trace
        info to all messages (if profiler is inited). And initialize profiler
        on callee side.

* **What points should be by default tracked**

   I think that for all projects we should include by default 3 kinds o points:

   * All HTTP calls

   * All RPC calls

   * All DB calls
