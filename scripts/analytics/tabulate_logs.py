# -*- coding: utf-8 -*-
"""Scripts for aggregating recently added logs by action type; pushes results
to the specified project.
"""

import bson
import datetime
from cStringIO import StringIO

import pymongo

from framework.mongo import database

from website import models
from website.app import app, init_app

from scripts.analytics import utils
from scripts.analytics import settings


mapper = bson.Code('''function() {
    emit(this.action, 1);
}''')


reducer = bson.Code('''function(key, values) {
    var count = 0;
    for (var i=0; i<values.length; i++) {
        count += values[i];
    }
    return count;
}''')


out = {'replace': settings.TABULATE_LOGS_RESULTS_COLLECTION}


def run_map_reduce(**kwargs):
    return database['nodelog'].map_reduce(
        mapper,
        reducer,
        out,
        **kwargs
    )


def main():
    node = models.Node.load(settings.TABULATE_LOGS_NODE_ID)
    user = models.User.load(settings.TABULATE_LOGS_USER_ID)
    cutoff = datetime.datetime.utcnow() - settings.TABULATE_LOGS_TIME_OFFSET
    result = run_map_reduce(query={'date': {'$gt': cutoff}})
    sio = StringIO()
    utils.make_csv(
        sio,
        (
            (row['_id'], row['value'])
            for row in result.find().sort([('value', pymongo.DESCENDING)])
        ),
        ['name', 'count'],
    )
    utils.create_object(
        settings.TABULATE_LOGS_FILE_NAME,
        settings.TABULATE_LOGS_CONTENT_TYPE,
        node, user, stream=sio, kind='file'
    )


if __name__ == '__main__':
    init_app()
    main()
