# -*- coding: utf-8 -*-
import gc

from website.app import init_app
from website import models

from modularodm import Q
from modularodm.storedobject import ensure_backrefs

def paginated(model, increment=200):
    last_id = ''
    pages = (model.find().count() / increment) + 1
    for i in xrange(pages):
        q = Q('_id', 'gt', last_id)
        page = list(model.find(q).limit(increment))
        for item in page:
            yield item
        if page:
            last_id = item._id

def main():
    init_app(routes=False)
    for i, record in enumerate(paginated(models.Node)):
        if i % 25 == 0:
            for key in ('node', 'user', 'fileversion', 'storedfilenode'):
                models.Node._cache.data.get(key, {}).clear()
                models.Node._object_cache.data.get(key, {}).clear()
            gc.collect()
        ensure_backrefs(record, ['logs'])
    print('Done.')

if __name__ == "__main__":
    main()
