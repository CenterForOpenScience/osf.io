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

    inv tests

To update the osf.io repo used for testing: ::

    inv setup_tests --update
