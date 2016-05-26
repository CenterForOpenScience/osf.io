# Scripts

This folder contains all miscellaneous scripts, clean ups, migrations, daily tasks, etc.


## Note for migrations

You'll want to follow the following template for migrations
It provides basic logging utilities and a dry run mode



```python
import sys
import logging
from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)


# This is where all your migration log will go
def do_migration():
    pass


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models

    # Start a transaction that will be rolled back if any exceptions are un
    with TokuTransaction():
        do_migration()
        if dry:
            # When running in dry mode force the transaction to rollback
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)

    # Allow setting the log level just by appending the level to the command
    if 'debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif 'warning' in sys.argv:
        logger.setLevel(logging.WARNING)
    elif 'info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif 'error' in sys.argv:
        logger.setLevel(logging.ERROR)

    # Finally run the migration
    main(dry=dry)
```


## Cursor timeouts

Sometimes and slowly iterating over a large collection the mongo cursor will time out

The code snippet below will paginate result and load them into memory so timeouts are no longer an issue

```python
from framework.mongo.utils import paginated
```

```python
def paginated(model, query=None, increment=200):
    last_id = ''
    pages = (model.find(query).count() / increment) + 1
    for i in xrange(pages):
        q = Q('_id', 'gt', last_id)
        if query:
            q &= query
        page = list(model.find(q).limit(increment))
        for item in page:
            yield item
        if page:
            last_id = item._id
```
