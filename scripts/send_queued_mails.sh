#!/bin/bash

export HOME="/home"
cd /opt/apps/osf
source /opt/data/envs/osf/bin/activate
python -m scripts.send_queued_mails
