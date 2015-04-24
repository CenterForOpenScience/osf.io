import logging

from framework.mongo import database
import pymongo

from website.app import init_app


logger = logging.getLogger(__name__)


def migrate():
    logger.info('migrating osfstorageguidfiles')

    try:
        database.osfstorageguidfile.drop_index(
            [
                ('node', pymongo.ASCENDING),
                ('path', pymongo.ASCENDING),
            ],
        )
    except pymongo.errors.OperationFailure:
        logger.warn('Index on node and path already removed')

    logger.info('path -> premigration_path')
    database.osfstorageguidfile.update({
        '_path': {'$ne': None}
    }, {
        '$rename': {'path': 'premigration_path'}
    }, multi=True)

    logger.info('_path -> path')
    database.osfstorageguidfile.update({
        '_path': {'$ne': None}
    }, {
        '$rename': {'_path': 'path'}
    }, multi=True)

    logger.info('migrating nodelogs')
    logger.info('params.path -> params.premigration_path')
    database.nodelog.update({
        'params._path': {'$ne': None}
    }, {
        '$rename': {'path': 'premigration_path'}
    }, multi=True)

    logger.info('params._path -> params.path')
    database.nodelog.update({
        'params._path': {'$ne': None}
    }, {
        '$rename': {'params._path': 'params.path'}
    }, multi=True)

    logger.info('params.urls -> params.premigration_urls')
    database.nodelog.update({
        'params._urls': {'$ne': None}
    }, {
        '$rename': {'params.urls': 'params.premigration_urls'}
    }, multi=True)

    logger.info('params._urls -> params.urls')
    database.nodelog.update({
        'params._urls': {'$ne': None}
    }, {
        '$rename': {'params._urls': 'params.urls'}
    }, multi=True)

def unmigrate():
    logger.info('unmigrating osfstorageguidfiles')
    logger.info('path -> _path')
    database.osfstorageguidfile.update({
        'premigration_path': {'$ne': None}
    }, {
        '$rename': {'path': '_path'}
    }, multi=True)

    logger.info('_path -> path')
    database.osfstorageguidfile.update({
        'premigration_path': {'$ne': None}
    }, {
        '$rename': {'premigration_path': 'path'}
    }, multi=True)

    logger.info('unmigrating nodelogs')
    logger.info('params.path -> params._path')
    database.nodelog.update({
        'params.premigration_path': {'$ne': None}
    }, {
        '$rename': {'path': '_path'}
    }, multi=True)

    logger.info('params.premigration_path -> params.path')
    database.nodelog.update({
        'params.premigration_path': {'$ne': None}
    }, {
        '$rename': {'params.premigration_path': 'params.path'}
    }, multi=True)

    logger.info('params.urls -> params._urls')
    database.nodelog.update({
        'params.premigration_urls': {'$ne': None}
    }, {
        '$rename': {'params.urls': 'params._urls'}
    }, multi=True)

    logger.info('params.premigration_urls -> params.urls')
    database.nodelog.update({
        'params.premigration_urls': {'$ne': None}
    }, {
        '$rename': {'params.premigration_urls': 'params.urls'}
    }, multi=True)

if __name__ == '__main__':
    import sys
    init_app(set_backends=True, routes=False)

    if 'reverse' in sys.argv:
        unmigrate()
    else:
        migrate()
