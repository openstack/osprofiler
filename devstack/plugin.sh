# DevStack extras script to install Rally

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

source $DEST/osprofiler/devstack/lib/osprofiler

if [[ "$1" == "source" ]]; then
    # Initial source
    source $TOP_DIR/lib/rally
# elif [[ "$1" == "stack" && "$2" == "install" ]]; then
#    echo_summary "Installing OSprofiler"
#    install_rally
elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    echo_summary "Configuring OSprofiler"
    configure_osprofiler
elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
    echo_summary "Initializing OSprofiler"
    init_osprofiler
fi

# Restore xtrace
$XTRACE
