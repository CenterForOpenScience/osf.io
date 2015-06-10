#!/bin/bash

export HOME=$(mktemp -d)
cd /opt/apps/osf
source /opt/data/envs/osf/bin/activate

python -m scripts.send_digest
