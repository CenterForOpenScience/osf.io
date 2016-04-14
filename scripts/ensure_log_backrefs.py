# -*- coding: utf-8 -*-
from website.app import init_app
from website import models
from modularodm.storedobject import ensure_backrefs

def main():
    init_app(routes=False)
    for record in models.Node.find():
        ensure_backrefs(record, ['logs'])
    print('Done.')

if __name__ == "__main__":
    main()
