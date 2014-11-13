"""Fixes nodes without is_folder set.

This script must be run from the OSF root directory for the imports to work.
"""

from framework.mongo import database


def main():

    database['node'].update({"is_folder": {'$exists': False}}, {'$set': {'is_folder': False}}, multi=True)
    database['node'].update({"is_dashboard": {'$exists': False}}, {'$set': {'is_dashboard': False}}, multi=True)

    database['node'].update({"expanded": {'$exists': False}}, {'$set': {'expanded': {}}}, multi=True)
    database['node'].update({"expanded": False}, {'$set': {'expanded': {}}}, multi=True)

    print('-----\nDone.')

if __name__ == '__main__':
    main()
