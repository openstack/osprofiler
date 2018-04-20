===========
Integration
===========

There are 4 topics related to integration OSprofiler & `OpenStack`_:

What we should use as a centralized collector?
----------------------------------------------

We primarily decided to use `Ceilometer`_, because:

* It's already integrated in OpenStack, so it's quite simple to send
  notifications to it from all projects.

* There is an OpenStack API in Ceilometer that allows us to retrieve all
  messages related to one trace. Take a look at
  *osprofiler.drivers.ceilometer.Ceilometer:get_report*

In OSProfiler starting with 1.4.0 version other options (MongoDB driver in
1.4.0 release, Elasticsearch driver added later, etc.) are also available.


How to setup profiler notifier?
-------------------------------

We primarily decided to use oslo.messaging Notifier API, because:

* `oslo.messaging`_ is integrated in all projects

* It's the simplest way to send notification to Ceilometer, take a
  look at: *osprofiler.drivers.messaging.Messaging:notify* method

* We don't need to add any new `CONF`_ options in projects

In OSProfiler starting with 1.4.0 version other options (MongoDB driver in
1.4.0 release, Elasticsearch driver added later, etc.) are also available.

How to initialize profiler, to get one trace across all services?
-----------------------------------------------------------------

To enable cross service profiling we actually need to do send from caller
to callee (base_id & trace_id). So callee will be able to init its profiler
with these values.

In case of OpenStack there are 2 kinds of interaction between 2 services:

* REST API

  It's well known that there are python clients for every project,
  that generate proper HTTP requests, and parse responses to objects.

  These python clients are used in 2 cases:

  * User access -> OpenStack

  * Service from Project 1 would like to access Service from Project 2


  So what we need is to:

  * Put in python clients headers with trace info (if profiler is inited)

  * Add `OSprofiler WSGI middleware`_ to your service, this initializes
    the profiler, if and only if there are special trace headers, that
    are signed by one of the HMAC keys from api-paste.ini (if multiple
    keys exist the signing process will continue to use the key that was
    accepted during validation).

    * The common items that are used to configure the middleware are the
      following (these can be provided when initializing the middleware
      object or when setting up the api-paste.ini file)::

          hmac_keys = KEY1, KEY2 (can be a single key as well)

  Actually the algorithm is a bit more complex. The Python client will
  also sign the trace info with a `HMAC`_ key (lets call that key ``A``)
  passed to profiler.init, and on reception the WSGI middleware will
  check that it's signed with *one of* the HMAC keys (the wsgi
  server should have key ``A`` as well, but may also have keys ``B``
  and ``C``) that are specified in api-paste.ini. This ensures that only
  the user that knows the HMAC key ``A`` in api-paste.ini can init a
  profiler properly and send trace info that will be actually
  processed. This ensures that trace info that is sent in that
  does **not** pass the HMAC validation will be discarded. **NOTE:** The
  application of many possible *validation* keys makes it possible to
  roll out a key upgrade in a non-impactful manner (by adding a key into
  the list and rolling out that change and then removing the older key at
  some time in the future).

* RPC API

  RPC calls are used for interaction between services of one project.
  It's well known that projects are using `oslo.messaging`_ to deal with
  RPC. It's very good, because projects deal with RPC in similar way.

  So there are 2 required changes:

  * On callee side put in request context trace info (if profiler was
    initialized)

  * On caller side initialize profiler, if there is trace info in request
    context.

  * Trace all methods of callee API (can be done via profiler.trace_cls).


What points should be tracked by default?
-----------------------------------------

I think that for all projects we should include by default 5 kinds of points:

* All HTTP calls - helps to get information about: what HTTP requests were
  done, duration of calls (latency of service), information about projects
  involved in request.

* All RPC calls - helps to understand duration of parts of request related
  to different services in one project. This information is essential to
  understand which service produce the bottleneck.

* All DB API calls - in some cases slow DB query can produce bottleneck. So
  it's quite useful to track how much time request spend in DB layer.

* All driver calls - in case of nova, cinder and others we have vendor
  drivers. Duration

* ALL SQL requests (turned off by default, because it produce a lot of
  traffic)

.. _CONF: https://docs.openstack.org/oslo.config/latest/
.. _HMAC: https://en.wikipedia.org/wiki/Hash-based_message_authentication_code
.. _OpenStack: https://www.openstack.org/
.. _Ceilometer: https://wiki.openstack.org/wiki/Ceilometer
.. _oslo.messaging: https://pypi.org/project/oslo.messaging
.. _OSprofiler WSGI middleware: https://github.com/openstack/osprofiler/blob/master/osprofiler/web.py
