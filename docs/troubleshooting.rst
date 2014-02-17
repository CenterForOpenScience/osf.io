Troubleshooting the OSF
=======================

This document is intended to serve as a knowledge repository - it should contain
solutions to commonly encountered problems when running the OSF, as well as
solutions to hard-to-debug issues that developers have encountered that might be
seen by others in the course of their work.

``ImportError: No module named five``
-------------------------------------

Celery may raise an exception when attempting to run the OSF tests. A partial
traceback::

    Exception occurred:
      File "<...>", line 49, in <module>
        from kombu.five import monotonic
    ImportError: No module named five