#!/bin/bash
# DevStack extras script to install osprofiler

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

source $DEST/osprofiler/devstack/lib/osprofiler

if [[ "$1" == "stack" && "$2" == "install" ]]; then
    echo_summary "Configuring system services for OSProfiler"
    install_osprofiler_collector

elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    echo_summary "Configuring OSProfiler"
    configure_osprofiler

elif [[ "$1" == "stack" && "$2" == "test-config" ]]; then
    echo_summary "Configuring Tempest"
    configure_osprofiler_in_tempest

fi

# Restore xtrace
$XTRACE
