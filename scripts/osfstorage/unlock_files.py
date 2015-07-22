import datetime

from modularodm import Q
from website.app import init_app
from website.addons.osfstorage import model
from framework.transactions.context import TokuTransaction

def main():
    locked_files = model.OsfStorageRentedFile.find(Q('state', 'eq', 'active'))
    for item in locked_files:
        if item.end_date < datetime.datetime.utcnow:
            with TokuTransaction():
                item.finish_rent()
                item.save()

if __name__ == '__main__':
    init_app()
    main()
