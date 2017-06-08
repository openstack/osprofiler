# DevStack extras script to install osprofiler

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

source $DEST/osprofiler/devstack/lib/osprofiler

if [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    echo_summary "Configuring OSprofiler"
    configure_osprofiler
fi

# Restore xtrace
$XTRACE
