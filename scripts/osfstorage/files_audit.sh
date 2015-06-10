#!/bin/bash

export HOME=$(mktemp -d)
cd /opt/apps/osf
source /opt/data/envs/osf/bin/activate

python -m scripts.osfstroage.files_audit 4 0 &
python -m scripts.osfstroage.files_audit 4 1 &
python -m scripts.osfstroage.files_audit 4 2 &
python -m scripts.osfstroage.files_audit 4 3 &
wait
