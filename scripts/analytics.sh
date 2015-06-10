#!/bin/bash

export HOME=$(mktemp)
cd /opt/apps/osf
source /opt/data/envs/osf/bin/activate

invoke analytics >> /var/log/osf/analytics.log 2>&1
