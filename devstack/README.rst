==================================
Enabling OSProfiler using DevStack
==================================

This directory contains the files necessary to run OpenStack with enabled
OSProfiler in DevStack.

OSProfiler has different drivers for trace processing. The default driver uses
Ceilometer to process and store trace events. Other drivers may connect
to databases directly and do not require Ceilometer.

To configure DevStack and enable OSProfiler edit ``${DEVSTACK_DIR}/local.conf``
file and add the following to ``[[local|localrc]]`` section:

  * to use specified driver::

    enable_plugin osprofiler https://git.openstack.org/openstack/osprofiler master
    OSPROFILER_CONNECTION_STRING=<connection string value>

    the driver is chosen depending on the value of
    ``OSPROFILER_CONNECTION_STRING`` variable (refer to the next section for
    details)

  * to use default Ceilometer driver::

    enable_plugin panko https://git.openstack.org/openstack/panko master
    enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer master
    enable_plugin osprofiler https://git.openstack.org/openstack/osprofiler master

  .. note:: The order of enabling plugins matters.

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
Default value is ``messaging://`` refers to Ceilometer driver. For a full
list of drivers please refer to
``http://git.openstack.org/cgit/openstack/osprofiler/tree/osprofiler/drivers``.
Example: enable ElasticSearch driver with the server running on localhost::

    OSPROFILER_CONNECTION_STRING=elasticsearch://127.0.0.1:9200

