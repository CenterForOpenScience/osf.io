#!/bin/bash

TEMPDIR=`mktemp -d`
trap "rm -rf $TEMPDIR" EXIT

export HOME=$TEMPDIR
cd /opt/apps/osf
source /opt/data/envs/osf/bin/activate

python -m scripts.osfstroage.files_audit 4 0 &
python -m scripts.osfstroage.files_audit 4 1 &
python -m scripts.osfstroage.files_audit 4 2 &
python -m scripts.osfstroage.files_audit 4 3 &
wait
