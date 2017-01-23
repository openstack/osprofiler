==================================
Enabling OSProfiler using DevStack
==================================

This directory contains the files necessary to run OpenStack with enabled
OSProfiler in DevStack.

To configure DevStack to enable OSProfiler edit
``${DEVSTACK_DIR}/local.conf`` file and add::

    enable_plugin panko https://git.openstack.org/openstack/panko master
    enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer master
    enable_plugin osprofiler https://git.openstack.org/openstack/osprofiler master

to the ``[[local|localrc]]`` section.

One can also configure a set of HMAC secrets, that are used for triggering of
profiling in OpenStack services: only the requests that specify one of these
keys in HTTP headers will be profiled. E.g. multiple secrets are specified as
a comma-separated list of string values::

    OSPROFILER_HMAC_KEYS=swordfish,foxtrot,charlie

.. note:: The order of enabling plugins matter.

Run DevStack as normal::

    $ ./stack.sh
