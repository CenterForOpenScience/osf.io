"""Fixes nodes without is_folder set.

This script must be run from the OSF root directory for the imports to work.
"""

from framework.mongo import database


def main():

    database['node'].update({"is_folder": {'$exists': False}}, {'$set': {'is_folder': False}}, multi=True)

    print('-----\nDone.')

if __name__ == '__main__':
    main()