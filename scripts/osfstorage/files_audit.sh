#!/bin/bash

# stop background processes if the shell is terminated
trap 'killall' INT
killall() {
    trap '' INT TERM     # ignore INT and TERM while shutting down
    kill -TERM 0         # fixed order, send TERM not INT
    wait
}

TEMPDIR=`mktemp -d`
trap "rm -rf $TEMPDIR" EXIT

export HOME=$TEMPDIR
cd /opt/apps/osf
source /opt/data/envs/osf/bin/activate

python -m scripts.osfstorage.files_audit 4 0 &
python -m scripts.osfstorage.files_audit 4 1 &
python -m scripts.osfstorage.files_audit 4 2 &
python -m scripts.osfstorage.files_audit 4 3 &
wait
