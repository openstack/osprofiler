==================================
Enabling OSProfiler using DevStack
==================================

This directory contains the files necessary to run OpenStack with enabled
OSProfiler in DevStack.

OSProfiler can send trace data into different collectors. There are 2 parameters
that control this:

* ``OSPROFILER_COLLECTOR`` specifies which collector to install in DevStack.
  By default OSProfiler plugin does not install anything, thus default
  messaging driver will be used.

  Possible values:

  * ``<empty>`` - default messaging driver is used
  * ``redis`` - Redis is installed
  * ``jaeger`` - Jaeger is installed
  * ``sqlalchemy`` - SQLAlchemy driver is installed

  The default value of ``OSPROFILER_CONNECTION_STRING`` is set automatically
  depending on ``OSPROFILER_COLLECTOR`` value.

* ``OSPROFILER_CONNECTION_STRING`` specifies which driver is used by OSProfiler.

  Possible values:

  * ``messaging://`` - use messaging as trace collector (with the transport configured by oslo.messaging)
  * ``redis://[:password]@host[:port][/db]`` - use Redis as trace storage
  * ``elasticsearch://host:port`` - use Elasticsearch as trace storage
  * ``mongodb://host:port`` - use MongoDB as trace storage
  * ``loginsight://username:password@host`` - use LogInsight as trace collector/storage
  * ``jaeger://host:port`` - use Jaeger as trace collector
  * ``mysql+pymysql://username:password@host/profiler?charset=utf8`` - use SQLAlchemy driver with MySQL database


To configure DevStack and enable OSProfiler edit ``${DEVSTACK_DIR}/local.conf``
file and add the following to ``[[local|localrc]]`` section:

* to use Redis collector::

      enable_plugin osprofiler https://opendev.org/openstack/osprofiler master
      OSPROFILER_COLLECTOR=redis

  OSProfiler plugin will install Redis and configure OSProfiler to use Redis driver

* to use specified driver::

      enable_plugin osprofiler https://opendev.org/openstack/osprofiler master
      OSPROFILER_CONNECTION_STRING=<connection string value>

  the driver is chosen depending on the value of
  ``OSPROFILER_CONNECTION_STRING`` variable (refer to the next section for
  details)


Run DevStack as normal::

    $ ./stack.sh


Config variables
----------------

**OSPROFILER_HMAC_KEYS** - a set of HMAC secrets, that are used for triggering
of profiling in OpenStack services: only the requests that specify one of these
keys in HTTP headers will be profiled. E.g. multiple secrets are specified as
a comma-separated list of string values::

    OSPROFILER_HMAC_KEYS=swordfish,foxtrot,charlie

**OSPROFILER_CONNECTION_STRING** - connection string to identify the driver.
Default value is ``messaging://`` refers to messaging driver. For a full
list of drivers please refer to
``https://opendev.org/openstack/osprofiler/src/branch/master/osprofiler/drivers``.
Example: enable ElasticSearch driver with the server running on localhost::

    OSPROFILER_CONNECTION_STRING=elasticsearch://127.0.0.1:9200

**OSPROFILER_COLLECTOR** - controls which collector to install into DevStack.
The driver is then chosen automatically based on the collector. Empty value assumes
that the default messaging driver is used.
Example: enable Redis collector::

    OSPROFILER_COLLECTOR=redis

**OSPROFILER_TRACE_SQLALCHEMY** - controls tracing of SQL statements. If enabled,
all SQL statements processed by SQL Alchemy are added into traces. By default enabled.
Example: disable SQL statements tracing::

    OSPROFILER_TRACE_SQLALCHEMY=False
