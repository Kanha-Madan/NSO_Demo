#!/usr/bin/env bash
# set -euo pipefail     u has been removed becoz it was letting any unamed to cause pipeline fail which we didn't need
set -eo pipefail

# loads my NSO commands and path variables
source "$(dirname "$0")/env.sh"           

#Will start our devices stored in netsim
ncs-netsim --dir "$NETSIM_DIR" start

#starts NSO from inside
(cd "$NCS_RUN" && ncs)

ncs_cli -C -u admin <<'EOF'

devices fetch-ssh-host-keys
devices sync-from
show devices list
EOF