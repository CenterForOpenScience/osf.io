#!/bin/bash

export HOME=$(mktemp)
cd /opt/apps/osf
source /opt/data/envs/osf/bin/activate

python -m scripts.send_digest
