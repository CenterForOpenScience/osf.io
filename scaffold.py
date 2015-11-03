import pymongo

from framework.mongo import client
from framework.mongo import database


if __name__ == '__main__':
    pymongo.MongoClient()

    # init_app(set_backends=False, routes=False)
    for key in settings.__dict__.keys():
        print('{}: {}'.format(key, settings[key]))
