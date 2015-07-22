import datetime

from modularodm import Q
from website.addons.osfstorage import model
from framework.transactions.context import TokuTransaction

def main():
    locked_files = model.OsfStorageRentedFile.find(Q('state', 'eq', 'active'))
    for file in locked_files:
        if file.end_date < datetime.datetime.utcnow:
            with TokuTransaction():
                file.finish_rent()
                file.save()

if __name__ == '__main__':
    main()
