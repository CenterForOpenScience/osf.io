# -*- coding: utf-8 -*-
import os
import json
import logging

from framework.mongo import database as db
from website import models
from website.app import init_app


FILE_NAME = 'logcounts.json'
logger = logging.getLogger()


def main():
    init_app()
    verify = os.path.exists(FILE_NAME)
    total = db.node.count()

    logger.info('{}unning in verify mode'.format('R' if verify else 'Not r'))

    counts = {}
    for i, node in enumerate(models.Node.find()):
        counts[node._id] = len(node.logs)
        if i % 5000 == 0:
            print('{:.2f}% finished'.format(float(i) / total * 100))
            models.Node._cache.data.clear()
            models.Node._object_cache.data.clear()

    if not verify:
        with open(FILE_NAME, 'w') as fobj:
            json.dump(counts, fobj)
    else:
        incorrect = []
        with open(FILE_NAME, 'r') as fobj:
            expected = json.load(fobj)
        for nid in (set(counts.keys()) | set(expected.keys())):
            if expected.get(nid, 0) != counts.get(nid, 0):
                incorrect.append({'id': nid, 'expected': expected.get(nid, 0), 'actual': counts.get(nid, 0)})
                logger.warning('Log count of node {} changed. Expected {} found {}'.format(nid, expected.get(nid, 0), counts.get(nid, 0)))
        if incorrect:
            logger.error('Found {} incorrect node log counts'.format(len(incorrect)))
            with open('incorrect.json', 'w') as fp:
                json.dump(incorrect, fp)
        else:
            logger.info('All counts match')


if __name__ == '__main__':
    main()
