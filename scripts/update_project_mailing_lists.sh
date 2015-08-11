#!/bin/bash

export HOME="/home"
cd /opt/apps/osf
source env/bin/activate
python -m scripts.update_project_mailing_lists
