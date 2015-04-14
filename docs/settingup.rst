Setting Up
==========

Make sure that you are using >= python3.3

Install requirements

.. code-block:: bash

    pip install -U -r requirements.txt

Or for some nicities

.. code-block:: bash

    pip install -U -r dev-requirements.txt

Required by the stevedore module. Allows for dynamic importing of providers

.. code-block:: bash

    python setup.py develop

Start the server

.. note

    The server is extremely tenacious thanks to stevedore and tornado
    Syntax errors in the :mod:`waterbutler.providers` will not crash the server
    In debug mode the server will automatically reload

.. code-block:: bash

    invoke server
