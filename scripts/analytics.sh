#!/bin/bash

export HOME="/home"
cd /opt/apps/osf
source mathenv/bin/activate
invoke analytics >> /var/log/osf/analytics.log 2>&1
