==================================
Enabling OSProfiler using DevStack
==================================

This directory contains the files necessary to run OpenStack with enabled
OSProfiler in DevStack.

To configure DevStack to enable OSProfiler edit
``${DEVSTACK_DIR}/local.conf`` file and add::

    enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer master
    enable_plugin panko https://git.openstack.org/openstack/panko master
    enable_plugin osprofiler https://git.openstack.org/openstack/osprofiler master

to the ``[[local|localrc]]`` section.

Run DevStack as normal::

    $ ./stack.sh
