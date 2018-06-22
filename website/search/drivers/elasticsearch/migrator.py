from __future__ import absolute_import

import re
import uuid
import abc

from django.db import connection
from django.db import transaction
from django.db.models import F, Value
from django.db.models import OuterRef, Subquery, Exists
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce, Concat
from elasticsearch import helpers

from osf.expressions import JSONBuildObject, ArrayAgg, JSONAgg
from osf.models import Node, Guid, NodeRelation, Contributor, OSFUser, AbstractNode, NodeLicenseRecord, NodeLicense, PreprintService, BaseFileNode

from website.search.drivers import base


class ElasticsearchMigrator(base.SearchMigrator):

    MAPPINGS = {
        'type': {'index': True, 'type': 'keyword'},

        'title': {'index': True, 'type': 'text', 'analyzer': 'english'},
        'description': {'index': True, 'type': 'text', 'analyzer': 'english'},

        'job': {'type': 'text', 'boost': 1.0},
        'all_jobs': {'type': 'text', 'boost': 0.01},
        'school': {'type': 'text', 'boost': 1.0},
        'all_schools': {'type': 'text', 'boost': 0.01},

        'tags': {'index': True, 'type': 'keyword'},
        'license': {
            'properties': {
                'id': {'index': True, 'type': 'keyword'},
                'name': {'index': True, 'type': 'keyword'},
                # Elasticsearch automatically infers mappings from content-type. `year` needs to
                # be explicitly mapped as a string to allow date ranges, which break on the inferred type
                'year': {'index': True, 'type': 'text'},
            }
        }
    }

    @property
    def _client(self):
        return self._driver._client

    @property
    def _index(self):
        return self._driver._index

    def setup(self):
        self._client.indices.create(
            index=self._index,
            body={
                'settings': {
                    # TODO
                },
                'mappings': {'doc': {'properties': self.MAPPINGS}},
                'aliases': {
                    # TODO
                },
            },
            ignore=[400]
        )

    def teardown(self):
        self._client.indices.delete(index=self._index, ignore=[404])

    def migrate_projects(self):
        x = 0
        for ok, response in helpers.streaming_bulk(self._client, ProjectActionGenerator(self._index, 'doc')):
            x += 1
            print(response)
        print('DID {} DOCUMENTS'.format(x))

    def migrate_components(self):
        x = 0
        for ok, response in helpers.streaming_bulk(self._client, ComponentActionGenerator(self._index, 'doc')):
            x += 1
            print(response)
        print('DID {} DOCUMENTS'.format(x))

    def migrate_registrations(self):
        pass

    def migrate_preprints(self):
        pass

    def migrate_files(self):
        pass

    def migrate_users(self):
        x = 0
        for ok, response in helpers.streaming_bulk(self._client, UserActionGenerator(self._index, 'doc')):
            x += 1
            print(response)
        print('DID {} DOCUMENTS'.format(x))

    def migrate_institutions(self):
        pass

class AbstractActionGenerator(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def type(self):
        raise NotImplementedError

    def __init__(self, index, doc_type, chunk_size=500):
        self._index = index
        self._doc_type = doc_type
        self._chunk_size = chunk_size

    @abc.abstractmethod
    def build_query(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def should_index(self, doc):
        raise NotImplementedError()

    def post_process(self, doc):
        return doc

    def guid_for(self, model, ref='pk'):
        return Subquery(
            Guid.objects.filter(
                object_id=OuterRef(ref),
                content_type__app_label=model._meta.app_label,
                content_type__model=model._meta.concrete_model._meta.model_name,
            ).values('_id')[:1]
        )

    def __iter__(self):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor_id = str(uuid.uuid4())
                query, params = self.build_query().query.sql_with_params()
                # Don't try this at home, kids
                cursor.execute('DECLARE "{}" CURSOR FOR {}'.format(cursor_id, query), params)

                # Should be able to use .iterator but it appears to be slower for whatever reason
                # TODO Investigate the above
                while True:
                    cursor.execute('FETCH {} FROM "{}"'.format(self._chunk_size, cursor_id))
                    rows = cursor.fetchall()

                    if not rows:
                        return

                    for row in rows:
                        if not row:
                            return

                        doc = row[0]
                        action = {'_id': doc.pop('_id'), '_index': self._index, '_type': self._doc_type}

                        if not self.should_index(doc):
                            action['_doc_type'] = 'delete'
                        else:
                            doc['type'] = self.type
                            action['_source'] = self.post_process(doc)
                            action['_doc_type'] = 'index'

                        yield action

class FileActionGenerator(AbstractActionGenerator):

    @property
    def type(self):
        return 'file'

    def build_query(self):
        return BaseFileNode.objects.annotate(
            _id=self.guid_for(BaseFileNode),
            name=F('name'),
            category=Value('name'),
            node=JSONBuildObject(
                title=F('node__title'),
                guid=self.guid_for(AbstractNode, 'node__pk'),
                type=F('node__type'),

            ),
            tags=Coalesce(Subquery(
                BaseFileNode.tags.through.objects.filter(
                    basefilenode_id=OuterRef('pk')
                ).annotate(
                    tags=ArrayAgg(F('tag__name'))
                ).values('tags')
            ), [])
        ).exclude(
            name=''
        ).values('doc')


class UserActionGenerator(AbstractActionGenerator):

    @property
    def type(self):
        return 'user'

    def build_query(self):
        return OSFUser.objects.annotate(
            doc=JSONBuildObject(
                _id=self.guid_for(OSFUser),
                user=F('fullname'),
                normalized_user=F('fullname'),  # TODO Legacy?
                normalized_names=JSONBuildObject(  # TODO Legacy?
                    fullname=F('fullname'),
                    given_name=F('given_name'),
                    family_name=F('family_name'),
                    middle_names=F('middle_names'),
                    suffix=F('suffix'),
                ),
                names=JSONBuildObject(
                    fullname=F('fullname'),
                    given_name=F('given_name'),
                    family_name=F('family_name'),
                    middle_names=F('middle_names'),
                    suffix=F('suffix'),
                ),
                jobs=F('jobs'),
                schools=F('schools'),
                social=F('social'),
            )
        ).values('doc')

    def should_index(self, doc):
        return True

    def post_process(self, doc):
        jobs = doc.pop('jobs')
        schools = doc.pop('schools')

        doc.update({
            'boost': 2,
            'category': 'user',  # TODO Legacy ?
            'job': jobs[0]['institution'] if jobs else '',
            'job_title': jobs[0]['title'] if jobs else '',
            'all_jobs': [x['institution'] for x in jobs[1:]],
            'school': schools[0]['institution'] if schools else '',
            'degree': schools[0]['degree'] if schools else '',
            'all_schools': [x['institution'] for x in schools],
            'social': {
                key: OSFUser.SOCIAL_FIELDS[key].format(val)
                if isinstance(val, basestring) else val
                for key, val in (doc.pop('social') or {}).items()
                if val and key in OSFUser.SOCIAL_FIELDS
            }
        })

        return doc


class NodeActionGenerator(AbstractActionGenerator):

    @abc.abstractproperty
    def category(self):
        raise NotImplementedError

    @abc.abstractmethod
    def _get_queryset(self):
        raise NotImplementedError

    @property
    def tags_query(self):
        return Coalesce(Subquery(
            AbstractNode.tags.through.objects.filter(
                abstractnode_id=OuterRef('pk')
            ).annotate(
                tags=ArrayAgg(F('tag__name'))
            ).values('tags')
        ), [])

    @property
    def affiliated_institutions_query(self):
        return Coalesce(Subquery(
            Node.affiliated_institutions.through.objects.filter(
                abstractnode_id=OuterRef('pk')
            ).annotate(
                names=ArrayAgg(F('institution__name'))
            ).values('names')
        ), [])

    @property
    def contributors_query(self):
        return Subquery(
            Contributor.objects.filter(
                node_id=OuterRef('pk'),
                visible=True,
            ).annotate(
                doc=JSONAgg(JSONBuildObject(
                    fullname=F('user__fullname'),
                    url=Concat(Value('/'), self.guid_for(OSFUser, 'user__pk'), Value('/')),
                ), order_by=F('_order').asc()),
            ).order_by().values('doc')
        )

    @property
    def parent_query(self):
        return Subquery(
            NodeRelation.objects.filter(
                child_id=OuterRef('pk')
            ).annotate(
                guid=self.guid_for(AbstractNode, 'parent_id')
            ).values('guid')[:1]
        )

    @property
    def preprint_query(self):
        return Subquery(PreprintService.objects.annotate(
            doc=JSONBuildObject(
                guid=self.guid_for(PreprintService),
                provider=JSONBuildObject(
                    # TODO _id
                    domain=F('provider__domain'),
                    domain_redirect_enabled=F('provider__domain_redirect_enabled'),
                )
            )
        ).filter(
            node_id=OuterRef('pk'),
            node__is_public=True,
            node___is_preprint_orphan=True,
        ).exclude(
            machine_state='initial',
        ).exclude(
            node__preprint_file_id=None,
        ).order_by(
            F('is_published').desc(),
            F('created').desc()
        ).values('doc')[:1].include(None))

    @property
    def license_query(self):
        return RawSQL(re.sub('\s+', ' ', '''(
            WITH RECURSIVE ascendants AS (
                SELECT
                    N.node_license_id,
                    R.parent_id
                FROM "{noderelation}" AS R
                    JOIN "{abstractnode}" AS N ON N.id = R.parent_id
                WHERE R.is_node_link IS FALSE
                    AND R.child_id = osf_abstractnode.id
            UNION ALL
                SELECT
                    N.node_license_id,
                    R.parent_id
                FROM ascendants AS D
                    JOIN "{noderelation}" AS R ON D.parent_id = R.child_id
                    JOIN "{abstractnode}" AS N ON N.id = R.parent_id
                WHERE R.is_node_link IS FALSE
                AND D.node_license_id IS NULL
            ) SELECT
                JSON_BUILD_OBJECT(
                    'id', LICENSE.license_id
                    , 'text', LICENSE.text
                    , 'name', LICENSE.name
                    , 'copyright_holders', NODE_LICENSE.copyright_holders
                    , 'year', NODE_LICENSE.year
                )
            FROM
                "{nodelicenserecord}" AS NODE_LICENSE
            JOIN
                "{nodelicense}" AS LICENSE
                ON NODE_LICENSE.node_license_id = LICENSE.id
            WHERE
                NODE_LICENSE.id = (SELECT node_license_id FROM ascendants WHERE node_license_id IS NOT NULL LIMIT 1)
            LIMIT 1
        )'''.format(
            nodelicense=NodeLicense._meta.db_table,
            noderelation=NodeRelation._meta.db_table,
            abstractnode=AbstractNode._meta.db_table,
            nodelicenserecord=NodeLicenseRecord._meta.db_table
        )), [])

    def should_index(self, doc):
        return True

    def build_query(self):
        return self._get_queryset().annotate(
            doc=JSONBuildObject(**self._build_attributes())
        ).values('doc')

    def _build_attributes(self):
        return {
            '_id': self.guid_for(AbstractNode),
            # Node Attrs
            'title': F('title'),
            'normalized_title': F('title'),  # TODO
            'public': F('is_public'),
            'date_created': F('created'),

            'boost': Value(2),  # Legacy?
            'category': Value(self.category),

            # Overriden in subclasses
            'is_registration': Value(False),
            'is_pending_registration': Value(False),
            'is_retracted': Value(False),
            'is_pending_retraction': Value(False),
            'embargo_end_date': Value(None),
            'is_pending_embargo': Value(False),
            'registered_date': Value(None),
            'wikis': Value(None),  # TODO

            # Relations
            'affiliated_institutions': self.affiliated_institutions_query,
            'contributors': self.contributors_query,
            'license': self.license_query,
            'preprint': self.preprint_query,
            'tags': self.tags_query,
            'parent_id': self.parent_query,  # TODO ???
            # 'extra_search_terms': clean_splitters(node.title), TODO
        }


class ProjectActionGenerator(NodeActionGenerator):

    @property
    def category(self):
        return 'project'

    @property
    def type(self):
        return 'project'

    def _get_queryset(self):
        return Node.objects.annotate(
            has_parent=Exists(NodeRelation.objects.filter(child_id=OuterRef('pk')))
        ).filter(
            has_parent=False,
            is_deleted=False,
        )

    def _build_attributes(self):
        return dict(
            super(ProjectActionGenerator, self)._build_attributes(),
            parent_id=Value(None)
        )

class ComponentActionGenerator(NodeActionGenerator):

    @property
    def category(self):
        return 'component'

    @property
    def type(self):
        return 'component'

    def _get_queryset(self):
        return Node.objects.annotate(
            has_parent=Exists(NodeRelation.objects.filter(child_id=OuterRef('pk')))
        ).filter(
            has_parent=True,
            is_deleted=False,
        )
