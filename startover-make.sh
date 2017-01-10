#!/bin/bash

python manage.py reset_db --noinput  && python manage.py migrate && python manage.py migratedata && python manage.py migratedata --nodelogs && python manage.py migraterelations
