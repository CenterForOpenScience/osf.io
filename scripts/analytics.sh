#!/bin/bash

export HOME="/home"
cd /opt/apps/osf
source /opt/data/envs/mathenv/bin/activate
invoke analytics >> /var/log/osf/analytics.log 2>&1
