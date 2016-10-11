**********
osf-models
**********

.. image:: https://travis-ci.org/CenterForOpenScience/osf-models.svg?branch=master
    :target: https://travis-ci.org/CenterForOpenScience/osf-models

**In progress** Django models for OSF.


Running tests
=============

First setup the tests. This only needs to be run once: ::

    inv setup_tests


Run the tests: ::

    inv test

To update the osf.io repo before testing: ::

    inv test --update


Running Migrations
==================

To create/reset your database: ::

    python manage.py reset_db --noinput

To migrate the defined schema to your database: ::

    python manage.py migrate

To migrate all models leaving their relationships empty: ::

    python manage.py migrate_bare_objects

To create foreign keys: ::

    python manage.py migrate_foreign_keys

To create many to many relationships: ::

    python manage.py migrate_m2m

To verify nodes and users: ::

    python manage.py verify_nodes_users

To create nodelogs: ::

    python manage.py migrate_nodelogs

To verify nodelogs: ::

    python manage.py verify_nodelogs
