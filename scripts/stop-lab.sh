#!/usr/bin/env bash
source "$(dirname "$0")/env.sh"

ncs --stop || true
ncs-netsim --dir "$NETSIM_DIR" stop || true