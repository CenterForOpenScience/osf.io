#!/bin/bash

TEMPDIR=`mktemp -d`
trap "rm -rf $TEMPDIR" EXIT

export HOME=$TEMPDIR
cd /opt/apps/osf
source /opt/data/envs/osf/bin/activate

mkdir -p $HOME/.config/matplotlib
invoke analytics >> /var/log/osf/analytics.log 2>&1
