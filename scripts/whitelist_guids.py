import csv

from framework.mongo import database as db
from website.app import init_app


def main():
    init_app(set_backends=True)
    clean_list = remove_current_guids('test.csv')
    create_whitelist_db_items(list(clean_list))


def remove_current_guids(file_name):
    whitelist = read_csv(file_name)
    current_guids = db['guid'].distinct('_id')
    return set(whitelist).difference(set(current_guids))


def read_csv(file_name):
    whitelist = []
    with open(file_name) as whitelist_csv:
        reader = csv.reader(whitelist_csv)
        for row in reader:
            for item in row:
                whitelist.append(item)
    return whitelist


def create_whitelist_db_items(clean_list):
    data = [{'_id': guid} for guid in clean_list]
    db.whitelistword.insert(data)


if __name__ == '__main__':
    main()