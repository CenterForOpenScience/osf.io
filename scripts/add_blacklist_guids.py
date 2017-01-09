import os
from framework.mongo import database as db
from website.app import init_app

HERE = os.path.dirname(os.path.abspath(__file__))
BLACKLIST_FILE = os.path.join(HERE, 'guid_blacklist.txt')


def main():
    init_app(set_backends=True)
    with open(BLACKLIST_FILE, 'r') as reader:
        blacklist = [item.rstrip('\n') for item in reader]

    chunk_size = len(blacklist)/4
    chunks = [blacklist[0:chunk_size], blacklist[chunk_size:(chunk_size*2)], blacklist[(chunk_size*2):(chunk_size*3)], blacklist[(chunk_size*3):]]
    for c in chunks:
        create_blacklist_guid_objects(c)


def create_blacklist_guid_objects(blacklist):
    data = [{'_id': guid} for guid in blacklist]
    db.blacklistguid.insert(data)


if __name__ == '__main__':
    main()
