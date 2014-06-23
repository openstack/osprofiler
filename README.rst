OSProfiler
==========

OSProfiler is an OpenStack cross-project profiling library.


Background
----------

OpenStack consists of multiple projects. Each project, in turn, has multiple services. To process some request, e.g. to boot a virtual machine, OpenStack uses multiple services from different projects. In case something works too slowly, it's extremely complicated to understand what exactly goes wrong and to locate the bottleneck.

To resolve this issue, we introduce a tiny but powerful library, **osprofiler**, that is going to be used by all OpenStack projects and their python clients. This library generates 1 trace per request, that goes through all services invoved, and builds a tree of calls (see an `example <http://pavlovic.me/rally/profiler/>`_).

*osprofiler* maintains a trace stack, which is shared between different services calling each other, thus being able to track nested method calls even across different OpenStack projects. By using a thread-safe storage, *osprofiler* takes care of the fact that each request to a certain service gets processed in a separated thread (so that each request results in a separate trace stack being maintained by this library).

*osproifiler* calls a special driver (*notify()*) on start & stop of every event. These notifications contain some special info that allows the user to track the stack of calls + meta info. In the case of OpenStack, notifications are expected to be sent to *Ceilometer* using the *oslo.messaging notifier API*. This enables to use *Ceilometer* as a centralized collecter, as well as to have an OpenStack API to retrieve all notifications related to one trace. To be more specific, *osprofiler* supports `retrieving all notifications in a single request <https://gist.github.com/boris-42/9a8f905d3c5bc7496984>`_ and, optionally, their analysis by producing a `tree of calls <https://gist.github.com/boris-42/c3c3ee1c2c7db40de236>`_.

To restrict its usage by non-allowed persons, *osprofiler* supports `HMAC authentication <http://en.wikipedia.org/wiki/Hash-based_message_authentication_code>`_. With this authentication mechanism enabled (and the same HMAC key set in the *osprofiler* section of the *api-paste.ini* file across all services involved), only users that know the HMAC key are able to use the profiling library and create traces.


Usage
-----

This simple example below demonstates how to use *osprofiler*, as well as what are the contents of the trace stack maintained by this library at each step:

.. parsed-literal::

    from osprofiler import profile

    profiler.init(base_id=1, parent_id=1)  *# Initializes a thread-safe stack for storing traces.*
                                           *# In case there is no init() call, all future start()/stop()*
                                           *# calls will be ignored by osprofiler.*

    *# stack = [1, 1]*

    profiler.start(name="code block 1")  *# stack = [1, 1, uuid1], sends notification with (base_id=1, parent_id=1, trace_id=uuid1)*

    profiler.start(name="code block 2")  *# stack = [1, 1, uuid1, uuid2], sends notification with (base_id=1, parent_id=uuid1, trace_id=uuid2)*
    profiler.stop()  *# stack = [1, 1, uuid1], sends notification with (base_id=1, parent_id=uuid1, trace_id=uuid2)*

    profiler.start(name="code block 3")  *# stack = [1, 1, uuid1, uuid3], sends notification with (base_id=1, parent_id=uuid1, trace_id=uuid3)*
    profiler.stop()  *# stack = [1, 1, rand1], sends notification with (base_id=1, parent_id=uuid1, trace_id=uuid3)*

    profiler.stop()  *# stack = [1, 1], sends notification with (base_id=1, parent_id=1, trace_id=1)*


After running this example, there will be 6 notifications for 3 events, and *osprofiler* will be able to restore the tree of calls, if needed.


The alternative syntax uses the `Trace object <https://github.com/stackforge/osprofiler/blob/master/osprofiler/profiler.py#L64>`_ from the profiler module, which should be used in a *with*-statement:


.. parsed-literal::

    from osprofiler import profiler

    ...

    with profiler.Trace(name="code block name", info={...}):
        *# Code to be profiled*


The following example shows a real custom *notification function* from the *oslo.messaging library*:


*oslo.messaging.profiler*

.. parsed-literal::

    **import osprofiler.notifier**

    **from oslo.messaging.notify import notifier**


    def set_notifier(context, transport, project, service, host):
        """Sets OSprofiler's notifer based on oslo.messaging notifier API.

        OSProfiler will call this method on every call of profiler.start() and
        profiler.stop(). These messages will be collected by Ceilometer, which
        which allows end users to retrieve traces via Ceilometer API.

        :context: the request context
        :transport: oslo.messaging transport
        :project: project name (e.g. nova, cinder, glance...)
        :service: service name, that sends notification (nova-conductor)
        :host: service's host name
        """

        *# Notifier based on oslo.messaging notifier API*
        **_notifier = notifier.Notifier(transport, publisher_id=host,
                                      driver="messaging", topic="profiler")**

        **def notifier_func(payload):**
            """This method will be called on profiler.start() and profiler.stop().

            :payload: Contains information about trace element.
                      In payload dict there are always 3 ids:
                      "base_id" - uuid that is common for all notifications related
                                  to one trace. Used to simplify retrieving of all
                                  trace elements from Ceilometer.
                      "parent_id" - uuid of parent element in trace
                      "trace_id" - uuid of current element in trace

                      Using parent_id and trace_id it's quite simple to build tree
                      of trace elements, which simplify analyze of trace.
            """
            payload["project"] = project
            payload["service"] = service
            _notifier.info(context, "profiler.%s" % service, payload)

        *# Setting the notifier function in osprofiler.*
        **osprofiler.notifier.set_notifier(notifier_func)**


This notifier is perfectly suited for integrating *osprofiler* with other OpenStack projects, e.g. Nova (the corresponding code sample can be found in the **Integration example** section below).



Library contents
----------------

Along with the basic profiling algorithm implementation, the *osprofiler* library includes a range of **profiling applications**, available out-of-box.

First, there is **SQLAlchemy profiling**. It's well known that OpenStack haevily uses *SQLAlchemy*. SQLAlchemy is a cool stuff that allows to add handlers for different events before and after SQL execution. With *osprofiler*, we can run *profiler.start()* before execution with info that contains an SQL request and call *profiler.stop()* after execution. This allows to collect the information about all DB calls across all services. To enable this DB profiling, just *osprofiler* to an **engine** instance (this will allow it to add event listeners to points before and after SQL execution):

.. parsed-literal::

    from osprofiler import sqlalchemy

    sqlalchemy.add_tracing(*<sqlalchemy_module>*, *<engine_instance>*, *<name>*)


Second, there is **Web profiling**. The main interaction mechanism between different OpenStack projects is issuing requests to each other. Thus, to be able to be easliy integrated with OpenStack projects, *osprofiler* supports processing such requests via a special **WSGI Middleware** for tracing Web applications:

.. parsed-literal::

    import webob.dec

    from osprofiler import profiler

    ...


    class WsgiMiddleware(object):
        """WSGI Middleware that enables tracing for an application."""

        ...

        @webob.dec.wsgify
        def __call__(self, request):
            if not self.enabled:
                return request.get_response(self.application)

            *# Trace info is passed through headers. In case the trace info header*
            *# is not present, no profiling will be done.*
            **trace_info_enc = request.headers.get("X-Trace-Info")**
            *# HMAC key is passed through headers as well.*
            **trace_hmac = request.headers.get("X-Trace-HMAC")**

            ...

            if trace_info_enc:
                trace_raw = utils.binary_decode(trace_info_enc)
                *# Validating the HMAC key.*
                try:
                    **validate_hmac(trace_raw, trace_hmac, self.hmac_key)**
                except IOError:
                    pass
                else:
                    trace_info = json.loads(trace_raw)

                    *# Initializing the profiler with the info retrieved from headers.*
                    **profiler.init(trace_info.get("base_id"),
                                  trace_info.get("parent_id"),
                                  self.hmac_key)**

                    *# The trace info that will be sent to the notifier.*
                    info = {
                        "request": {
                            "host_url": request.host_url,
                            "path": request.path,
                            "query": request.query_string,
                            "method": request.method,
                            "scheme": request.scheme
                        }
                    }

                    *# Profiling the request.*
                    **with profiler.Trace(self.name, info=info):
                        return request.get_response(self.application)**

            *# If there is no trace info header, just process the request without profiling.*
            return request.get_response(self.application)


Integration example
-------------------

**OSProfiler** can be easily integrated with any of the core OpenStack projects, e.g. `Nova <https://github.com/boris-42/nova/commit/9ebe86bf5b4cc7150251396cfb302dd05e89085d>`_. Basically, it requires setting up the corresponding notifier function for the *WSGI service*, and then adding the *osprofiler WSGI middleware* in a special *api-paste.ini* file. The example below shows how it looks for Nova:


*nova.service*

.. parsed-literal::

    ...

    from oslo.messaging import profiler


    class Service(service.Service):
        """Service object for binaries running on hosts."""

        def __init__(self, host, binary, topic, manager, ...):

            ...

            *# Set the notifier function with the admin request context*
            *# and corresponding project & service parameters*
            **profiler.set_notifier(context.get_admin_context().to_dict(),
                                  rpc.TRANSPORT, "nova", binary, host)**
            ...


    class WSGIService(object):
        """Provides ability to launch API from a 'paste' configuration."""

        def __init__(self, name, loader=None, use_ssl=False, max_url_len=None):

            ...

            *# Set the notifier function with the admin request context*
            *# and corresponding project & service parameters*
            **profiler.set_notifier(context.get_admin_context().to_dict(),
                                  rpc.TRANSPORT, "nova", name, self.host)**
            ...


*etc/nova/api-paste.ini*

.. parsed-literal::

    ...
    [composite:openstack_compute_api_v2]
    use = call:nova.api.auth:pipeline_factory
    noauth = compute_req_id faultwrap sizelimit **osprofiler** noauth ...
    keystone = compute_req_id faultwrap sizelimit **osprofiler** authtoken ...
    keystone_nolimit = compute_req_id faultwrap sizelimit **osprofiler** authtoken ...

    ...
    [filter:osprofiler]
    paste.filter_factory = osprofiler.web:WsgiMiddleware.factory
    hmac_key = SECRET_KEY
    enabled = yes
