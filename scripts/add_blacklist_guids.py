from framework.mongo import database as db
from website.app import init_app

blacklist_file = 'guid_blacklist.txt'


def main():
    init_app(set_backends=True)
    with open(blacklist_file, 'r') as reader:
        blacklist = [item.rstrip('\n') for item in reader]
    create_blacklist_guid_objects(list(blacklist))


def create_blacklist_guid_objects(blacklist):
    data = [{'_id': guid} for guid in blacklist]
    db.blacklistguid.insert(data)


if __name__ == '__main__':
    main()