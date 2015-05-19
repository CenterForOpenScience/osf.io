from modularodm.storage.base import KeyExistsException

from framework.guid.model import WhitelistWord
from website.app import init_app

# List of language-safe guids
WHITELIST = ['test1', 'test2', 'test3']


def main():
    init_app(set_backends=True)
    create_whitelist_db_items()


def create_whitelist_db_items():
    for word in WHITELIST:
        try:
            w = WhitelistWord(_id=word)
            w.save()
        except KeyExistsException:
            pass

if __name__ == '__main__':
    main()