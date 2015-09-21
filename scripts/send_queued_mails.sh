#!/bin/bash

export HOME="/home"
cd /opt/apps/osf
source env/bin/activate
python -m scripts.send_queued_mail
