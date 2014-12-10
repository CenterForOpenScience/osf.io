# -*- coding: utf-8 -*-
"""Scripts for aggregating recently added logs by action type; pushes results
to the specified project.
"""

import bson
import datetime

import pymongo
from dateutil.relativedelta import relativedelta

from framework.mongo import database

from website import models
from website.app import app, init_app

from scripts.analytics import utils


RESULTS_COLLECTION = 'logmetrics'
TIME_OFFSET = relativedelta(days=1)
NUM_ROWS = 20

FILE_NAME = 'log-counts.csv'
CONTENT_TYPE = 'text/css'
NODE_ID = '95nv8'
USER_ID = 'icpnw'


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


def run_map_reduce(**kwargs):
    return database['nodelog'].map_reduce(
        mapper,
        reducer,
        RESULTS_COLLECTION,
        **kwargs
    )


def main():
    node = models.Node.load(NODE_ID)
    user = models.User.load(USER_ID)
    cutoff = datetime.datetime.utcnow() - TIME_OFFSET
    result = run_map_reduce(query={'date': {'$gt': cutoff}})
    sio, nchar = utils.make_csv(
        (
            (row['_id'], row['value'])
            for row in result.find().sort([('value', pymongo.DESCENDING)])
        ),
        ['name', 'count'],
    )
    utils.send_file(app, FILE_NAME, CONTENT_TYPE, sio, nchar, node, user)


if __name__ == '__main__':
    app = init_app()
    main()
