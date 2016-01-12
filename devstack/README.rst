==================================
Enabling OSprofiler using DevStack
==================================

This directory contains the files necessary to run OpenStack with enabled
OSprofiler in DevStack.

To configure DevStack to enable OSprofiler edit
``${DEVSTACK_DIR}/local.conf`` file and add::

    enable_plugin ceilometer https://github.com/openstack/ceilometer master
    enable_plugin osprofiler https://github.com/openstack/osprofiler master

to the ``[[local|localrc]]`` section.

Run DevStack as normal::

    $ ./stack.sh
