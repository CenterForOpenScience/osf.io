from __future__ import absolute_import

import re
import uuid

from django.db import connection
from django.db import transaction
from django.db.models import Func, F, Value
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce, Concat
from django.db.models import OuterRef, Subquery, Exists
from django.contrib.postgres.fields import JSONField
from elasticsearch import helpers
import elasticsearch

from website.search.drivers import base
from website.search.drivers.elasticsearch.migrator import ElasticsearchMigrator

from osf.expressions import JSONBuildObject, ArrayAgg, JSONAgg
from osf.models import Node, Guid, NodeRelation, Contributor, OSFUser, AbstractNode, NodeLicenseRecord, NodeLicense, PreprintService

class ElasticsearchDriver(base.SearchDriver):

    @property
    def migrator(self):
        return ElasticsearchMigrator(self)

    def __init__(self, index):
        self._index = index
        self._client = elasticsearch.Elasticsearch([
            'http://localhost:9201'
        ])

    def bulk_update_nodes(self):
        pass
    def create_index(self):
        pass
    def delete_all(self):
        pass
    def delete_index(self):
        pass
    def delete_node(self):
        pass
    def search(self):
        pass
    def search_contributor(self):
        pass
    def update_contributors_async(self):
        pass
    def update_file(self):
        pass
    def update_institution(self):
        pass
    def update_node(self):
        pass
    def update_user(self):
        pass
