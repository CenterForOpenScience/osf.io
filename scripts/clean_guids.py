import csv

from framework.mongo import database as db
from website.app import init_app


def main():
    init_app(set_backends=True)
    clean_list = remove_current_guids('test.csv')
    create_clean_guid_objects(list(clean_list))


def remove_current_guids(file_name):
    clean_guids = read_csv(file_name)
    current_guids = db['guid'].distinct('_id')
    return set(clean_guids).difference(set(current_guids))


def read_csv(file_name):
    clean_guids = []
    with open(file_name) as whitelist_csv:
        reader = csv.reader(whitelist_csv)
        for row in reader:
            for item in row:
                clean_guids.append(item)
    return clean_guids


def create_clean_guid_objects(clean_list):
    data = [{'_id': guid} for guid in clean_list]
    db.cleanguid.insert(data)


if __name__ == '__main__':
    main()