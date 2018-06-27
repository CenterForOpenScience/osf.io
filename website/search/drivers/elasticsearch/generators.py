from __future__ import absolute_import

import abc
import re
import uuid

from django.db import connection
from django.db import transaction
from django.db.models import F, Value, When, Case
from django.db.models import OuterRef, Subquery, Exists
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce, Concat

from addons.wiki.models import WikiPage, WikiVersion

from osf.expressions import JSONBuildObject, ArrayAgg, JSONAgg
from osf import models
from osf.utils.workflows import DefaultStates
from osf.models import Node, Guid, NodeRelation, Contributor, OSFUser, AbstractNode, NodeLicenseRecord, NodeLicense, PreprintService, BaseFileNode, Institution

from website import settings


class AbstractActionGenerator(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def type(self):
        raise NotImplementedError

    def __init__(self, index, doc_type, chunk_size=1000):
        self._index = index
        self._doc_type = doc_type
        self._chunk_size = chunk_size

    @abc.abstractmethod
    def build_query(self):
        raise NotImplementedError()

    def should_index(self, doc):
        return True

    def post_process(self, _id, doc):
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
                            action['_source'] = self.post_process(action['_id'], doc)
                            action['_doc_type'] = 'index'

                        yield action


class FileActionGenerator(AbstractActionGenerator):

    @property
    def type(self):
        return 'file'

    @property
    def tags_query(self):
        return Coalesce(Subquery(
            BaseFileNode.tags.through.objects.filter(
                basefilenode_id=OuterRef('pk')
            ).annotate(
                tags=ArrayAgg(F('tag__name'))
            ).values('tags')
        ), [])

    @property
    def retracted_query(self):
        return RawSQL(re.sub('\s+', ' ', '''(
            WITH RECURSIVE ascendants AS (
                SELECT
                    N.retraction_id,
                    R.parent_id
                FROM "{abstractnode}" AS N
                  LEFT OUTER JOIN "{noderelation}" AS R ON N.id = R.child_id
                WHERE N.id = "{abstractnode}".id AND (R IS NULL OR R.is_node_link = FALSE)
            UNION ALL
                SELECT
                    N.retraction_id,
                    R.parent_id
                FROM ascendants AS D
                    JOIN "{abstractnode}" AS N ON N.id = D.parent_id
                    LEFT OUTER JOIN "{noderelation}" AS R ON D.parent_id = R.child_id
                WHERE D.retraction_id IS NULL AND (R IS NULL OR R.is_node_link = FALSE)
            ) SELECT
                RETRACTION.state = '{approved}' AS is_retracted
            FROM
                osf_retraction AS RETRACTION
            WHERE
                RETRACTION.id = (SELECT retraction_id FROM ascendants WHERE retraction_id IS NOT NULL LIMIT 1)
            LIMIT 1
        )'''.format(
            abstractnode=AbstractNode._meta.db_table,
            approved=models.Retraction.APPROVED,
            noderelation=NodeRelation._meta.db_table,
            retraction=models.Retraction._meta.db_table,
        )), [])

    @property
    def node_query(self):
        return JSONBuildObject(
            title=F('node__title'),
            guid=self.guid_for(AbstractNode, 'node__pk'),
            type=F('node__type'),
            is_retracted=Coalesce(self.retracted_query, Value(False)),
            parent_guid=Subquery(
                NodeRelation.objects.filter(
                    is_node_link=False,
                    child_id=OuterRef('node__pk')
                ).annotate(
                    guid=self.guid_for(AbstractNode, 'parent_id')
                ).order_by('created').values('guid')[:1]
            )
        )

    def build_query(self):
        qs = BaseFileNode.objects.all()

        # NOTE: A file will be exclude from search if any of the following apply
        # File Based Exclusions:
        # * File is tagged with anything in settings.DO_NOT_INDEX_LIST['tags']
        # * File is NOT and OSFStorageFile
        # * File is deleted (Techinically covered by the above)
        # Node Based Exclusions:
        # * Node is deleted
        # * Node is not public
        # * Node is tagged with anything settings.DO_NOT_INDEX_LIST['tags'] (Currently qatest and qa test)
        # * Node has a title that contains anything in settings.DO_NOT_INDEX_LIST['titles'] (Case insensitive)
        # * Node is "spammy" (spam_status = 1) and settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH is true
        # * Node is spam (spam_status = 2)
        # * Node is in the process of being archived
        # * Node failed to archive

        for title in settings.DO_NOT_INDEX_LIST['titles']:
            qs = qs.exclude(node__title__icontains=title)

        if settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH:
            qs = qs.exclude(node__spam_status=1)

        return qs.annotate(
            doc=JSONBuildObject(
                _id=F('_id'),
                guid=self.guid_for(BaseFileNode),
                name=F('name'),
                category=Value('file'),
                tags=self.tags_query,
                node=self.node_query,
            ),
            file_qa_tags=Exists(BaseFileNode.tags.through.objects.filter(
                basefilenode_id=OuterRef('pk'),
                tag__name__in=settings.DO_NOT_INDEX_LIST['tags'],
            )),
            node_qa_tags=Exists(AbstractNode.tags.through.objects.filter(
                abstractnode_id=OuterRef('node__pk'),
                tag__name__in=settings.DO_NOT_INDEX_LIST['tags'],
            )),
            is_archiving_or_failed=Exists(models.ArchiveJob.objects.filter(
                dst_node_id=OuterRef('node__pk'),
            ).exclude(
                status='SUCCESS'
            )),
        ).filter(
            is_archiving_or_failed=False,  # Node may not be in the processes of archiving or have failed to archive
            node__is_deleted=False,  # Node may not be deleted
            name__isnull=False,  # Name may not be null
            file_qa_tags=False,  # File may not have QA tags
            node_qa_tags=False,  # Node may not have QA tags
            node__is_public=True,  # Node must be public to index files
            type='osf.osfstoragefile',  # Only OSFStorage Files for now
        ).exclude(
            name=''
        ).exclude(
            node__spam_status=2
        ).values('doc')

    def post_process(self, _id, doc):
        node = doc.pop('node')
        guid = doc.pop('guid', None)

        extra = doc['name'].replace('_', ' ').replace('-', ' ').replace('.', ' ')
        if extra == doc['name']:
            extra = ''

        doc.update({
            'deep_url': '/{}/files/osfstorage/{}'.format(node['guid'], _id),
            'guid_url': '/{}/'.format(guid) if guid else None,
            'is_registration': node['type'] == models.Registration._meta.label_lower,
            'is_retracted': node['is_retracted'],
            'node_title': node['title'],
            'node_url': '/{}/'.format(node['guid']),
            'parent_id': node['parent_guid'],
            'extra_search_terms': extra,
        })

        return doc


class InstitutionActionGenerator(AbstractActionGenerator):

    @property
    def type(self):
        return 'institution'

    def build_query(self):
        return Institution.objects.annotate(
            doc=JSONBuildObject(
                _id=F('_id'),
                category=Value('institution'),
                name=F('name'),
                logo_name=F('logo_name'),
            )
        ).filter(is_deleted=False).values('doc')

    def post_process(self, _id, doc):
        doc['url'] = '/institutions/{}/'.format(_id)
        logo_name = doc.pop('logo_name')
        if logo_name:
            doc['logo_path'] = '/static/img/institutions/shields/{}'.format(logo_name)
        else:
            doc['logo_path'] = None
        return doc


class NodeCollectionSubmition(AbstractActionGenerator):

    @property
    def type(self):
        return 'collectionSubmission'

    @property
    def subjects_query(self):
        return Coalesce(Subquery(
            models.CollectedGuidMetadata.subjects.through.objects.filter(
                collectedguidmetadata_id=OuterRef('pk'),
            ).annotate(
                doc=ArrayAgg('subject__text')
            ).values('doc')
        ), Value([]))

    @property
    def node_query(self):
        return 


    @property
    def contributors_query(self):
        return Subquery(
            models.Contributor.objects.filter(
                visible=True,
                node_id=OuterRef('object_id'),
            ).annotate(
                doc=JSONAgg(JSONBuildObject(
                    fullname=F('user__fullname'),
                    is_active=F('user__is_active'),
                    guid=self.guid_for(models.OSFUser, 'user__pk'),
                ), order_by=F('_order').asc())
            ).order_by().values('doc')
        )

    def build_query(self):
        return models.CollectedGuidMetadata.objects.filter(
            collection__deleted__isnull=True,
            collection__is_bookmark_collection=False,
            collection__is_public=True,
            collection__provider__isnull=False,
            guid__content_type__model=models.AbstractNode._meta.model_name,
            guid__content_type__app_label=models.AbstractNode._meta.app_label,
        ).annotate(
            doc=JSONBuildObject(
                _id=Concat(
                    F('guid___id'),
                    Value('-'),
                    self.guid_for(models.Collection, 'collection__pk'),
                ),
                status=F('status'),
                category=Value('collectionSubmission'),
                collectedType=F('collected_type'),
                subjects=self.subjects_query,
                node=Subquery(
                    Guid.objects.degeneric(referent=models.AbstractNode).filter(
                        pk=OuterRef('guid__id')
                    ).annotate(
                        doc=JSONBuildObject(
                            guid=F('_id'),
                            title=F('referent__title'),
                            description=F('referent__description'),
                            contributors=self.contributors_query,
                        )
                    ).values('doc')
                )
            )
        ).values('doc')

    def post_process(self, _id, doc):
        node = doc.pop('node')

        doc['title'] = node['title']
        doc['abstract'] = node['description']
        doc['url'] = '/{}/'.format(node['guid'])

        doc['contributors'] = [{
            'fullname': contrib['fullname'],
            'url': '/{}/'.format(contrib['guid']) if contrib['is_active'] else None
        } for contrib in node['contributors']]

        return doc


class UserActionGenerator(AbstractActionGenerator):

    @property
    def type(self):
        return 'user'

    def build_query(self):
        return models.OSFUser.objects.annotate(
            doc=JSONBuildObject(
                _id=self.guid_for(models.OSFUser),
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
        ).filter(is_active=True).values('doc')

    def post_process(self, _id, doc):
        jobs = doc.pop('jobs')
        schools = doc.pop('schools')

        # NOTE: all the else '' and or None are to preserve
        # existing behavior
        doc.update({
            'boost': 2,
            'category': 'user',  # TODO Legacy ?
            'job': jobs[0]['institution'] if jobs else '',
            'job_title': jobs[0]['title'] if jobs else '',
            'all_jobs': [x['institution'] for x in jobs] or None,
            'school': schools[0]['institution'] if schools else '',
            'degree': schools[0]['degree'] if schools else '',
            'all_schools': [x['institution'] for x in schools] or None,
            'social': {
                key: OSFUser.SOCIAL_FIELDS[key].format(val)
                if isinstance(val, basestring) else val
                for key, val in (doc.pop('social') or {}).items()
                if val and key in OSFUser.SOCIAL_FIELDS
            } or None
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
                tag__system=False,
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
            models.Contributor.objects.filter(
                node_id=OuterRef('pk'),
                visible=True,
            ).annotate(
                doc=JSONAgg(JSONBuildObject(
                    fullname=F('user__fullname'),
                    url=Case(
                        When(
                            user__is_active=True,
                            then=Concat(Value('/'), self.guid_for(OSFUser, 'user__pk'), Value('/'))
                        ),
                        default=Value(None)
                    )
                ), order_by=F('_order').asc()),
            ).order_by().values('doc')
        )

    @property
    def parent_query(self):
        return Subquery(
            NodeRelation.objects.filter(
                is_node_link=False,
                child_id=OuterRef('pk')
            ).annotate(
                guid=self.guid_for(AbstractNode, 'parent_id')
            ).values('guid')[:1]
        )

    @property
    def license_query(self):
        return RawSQL(re.sub('\s+', ' ', '''(
            WITH RECURSIVE ascendants AS (
                SELECT
                    N.id,
                    N.node_license_id
                FROM "{abstractnode}" AS N
                WHERE N.id = "{abstractnode}".id
            UNION ALL
                SELECT
                    N.id,
                    N.node_license_id
                FROM ascendants AS D
                    JOIN "{noderelation}" AS R ON R.child_id = D.id
                    JOIN "{abstractnode}" AS N ON N.id = R.parent_id
                WHERE D.node_license_id IS NULL AND R.is_node_link = FALSE
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

    def post_process(self, _id, doc):
        doc['url'] = '/{}/'.format(_id)
        if not doc['license']:
            doc['license'] = {
                'copyright_holders': None,
                'id': None,
                'name': None,
                'text': None,
                'year': None,
            }

        extra = doc['title'].replace('_', ' ').replace('-', ' ').replace('.', ' ')
        if extra == doc['title']:
            extra = ''

        doc['extra_search_terms'] = extra

        preprint = doc.pop('preprint', None)
        if preprint:
            provider = preprint['provider']
            if (provider['domain_redirect_enabled'] and provider['domain']) or provider['_id'] == 'osf':
                doc['preprint_url'] = '/{}/'.format(preprint['guid'])
            else:
                doc['preprint_url'] = '/preprints/{}/{}/'.format(provider['_id'], preprint['guid'])
        else:
            doc['preprint_url'] = None

        if doc.pop('type') == 'osf.node':
            doc['boost'] = 2
        else:
            doc['boost'] = 1

        doc['wikis'] = {
            # TODO Sanatize?
            x['name'].replace('.', ' '): x['content']
            for x in (doc['wikis'] or [])
            if x['name'].replace('.', ' ').strip()
        }

        return doc

    def _build_attributes(self):
        return {
            '_id': self.guid_for(AbstractNode),
            'type': F('type'),
            # Node Attrs
            'title': F('title'),
            'description': F('description'),
            'normalized_title': F('title'),  # TODO
            'public': F('is_public'),
            'date_created': F('created'),

            'category': Value(self.category),

            # Overriden in subclasses
            'is_registration': Value(False),
            'is_pending_registration': Value(False),
            'is_retracted': Value(False),
            'is_pending_retraction': Value(False),
            'embargo_end_date': Value(None),
            'is_pending_embargo': Value(False),
            'registered_date': Value(None),
            'wikis': Subquery(WikiPage.objects.annotate(
                doc=JSONAgg(JSONBuildObject(
                    name=F('page_name'),
                    content=Subquery(WikiVersion.objects.filter(
                        wiki_page_id=OuterRef('pk')
                    ).order_by('-created').values('content')[:1])
                ))
            ).filter(
                node_id=OuterRef('pk')
            ).values('doc')),

            # Value(None),  # TODO

            # Relations
            'affiliated_institutions': self.affiliated_institutions_query,
            'contributors': self.contributors_query,
            'license': self.license_query,
            'tags': self.tags_query,
            'parent_id': self.parent_query,  # TODO ???
        }


class ProjectActionGenerator(NodeActionGenerator):

    @property
    def category(self):
        return 'project'

    @property
    def type(self):
        return 'project'

    def _get_queryset(self):
        qs = AbstractNode.objects.annotate(
            has_parent=Exists(NodeRelation.objects.filter(child_id=OuterRef('pk'), is_node_link=False)),
            has_qa_tags=Exists(AbstractNode.tags.through.objects.filter(
                abstractnode_id=OuterRef('pk'),
                tag__name__in=settings.DO_NOT_INDEX_LIST['tags'],
            )),
            has_preprint=Exists(PreprintService.objects.filter(
                node_id=OuterRef('pk')
            ).exclude(
                machine_state=DefaultStates.INITIAL.value,
            )),
            is_archiving_or_failed=Exists(models.ArchiveJob.objects.filter(
                dst_node_id=OuterRef('pk'),
            ).exclude(
                status='SUCCESS'
            )),
        ).filter(
            # TODO Remove quickfiles
            type__in=['osf.node', 'osf.quickfilesnode'],
            is_public=True,
            is_deleted=False,
            is_archiving_or_failed=False,
            has_qa_tags=False,
            has_parent=False,
        ).exclude(
            spam_status=2
        ).exclude(
            _is_preprint_orphan=False,
            has_preprint=True,
            preprint_file_id__isnull=False,
        )

        for title in settings.DO_NOT_INDEX_LIST['titles']:
            qs = qs.exclude(title__icontains=title)

        if settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH:
            qs = qs.exclude(spam_status=1)

        return qs

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
        qs = Node.objects.annotate(
            has_parent=Exists(NodeRelation.objects.filter(child_id=OuterRef('pk'), is_node_link=False)),
            has_qa_tags=Exists(AbstractNode.tags.through.objects.filter(
                abstractnode_id=OuterRef('pk'),
                tag__name__in=settings.DO_NOT_INDEX_LIST['tags'],
            )),
            has_preprint=Exists(PreprintService.objects.filter(
                node_id=OuterRef('pk')
            ).exclude(
                machine_state=DefaultStates.INITIAL.value,
            )),
            is_archiving_or_failed=Exists(models.ArchiveJob.objects.filter(
                dst_node_id=OuterRef('pk'),
            ).exclude(
                status='SUCCESS'
            )),
        ).filter(
            is_public=True,
            is_deleted=False,
            is_archiving_or_failed=False,
            has_qa_tags=False,
            has_parent=True,
        ).exclude(
            spam_status=2
        ).exclude(
            _is_preprint_orphan=False,
            has_preprint=True,
            preprint_file_id__isnull=False,
        )

        for title in settings.DO_NOT_INDEX_LIST['titles']:
            qs = qs.exclude(title__icontains=title)

        if settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH:
            qs = qs.exclude(spam_status=1)

        return qs


class PreprintActionGenerator(NodeActionGenerator):

    @property
    def category(self):
        return 'preprint'

    @property
    def type(self):
        return 'preprint'

    @property
    def preprint_query(self):
        return Subquery(PreprintService.objects.annotate(
            doc=JSONBuildObject(
                guid=self.guid_for(PreprintService),
                provider=JSONBuildObject(
                    _id=F('provider___id'),
                    domain=F('provider__domain'),
                    domain_redirect_enabled=F('provider__domain_redirect_enabled'),
                )
            )
        ).filter(
            node_id=OuterRef('pk'),
        ).order_by(
            F('is_published').desc(),
            F('created').desc()
        ).values('doc')[:1])

    def _get_queryset(self):
        qs = Node.objects.annotate(
            has_qa_tags=Exists(AbstractNode.tags.through.objects.filter(
                abstractnode_id=OuterRef('pk'),
                tag__name__in=settings.DO_NOT_INDEX_LIST['tags'],
            )),
            has_preprint=Exists(PreprintService.objects.filter(
                node_id=OuterRef('pk')
            ).exclude(
                machine_state=DefaultStates.INITIAL.value,
            )),
            is_archiving_or_failed=Exists(models.ArchiveJob.objects.filter(
                dst_node_id=OuterRef('pk'),
            ).exclude(
                status='SUCCESS'
            )),
        ).filter(
            is_public=True,
            is_deleted=False,
            is_archiving_or_failed=False,
            has_qa_tags=False,
            _is_preprint_orphan=False,
            has_preprint=True,
            preprint_file_id__isnull=False,
        ).exclude(
            spam_status=2
        )

        for title in settings.DO_NOT_INDEX_LIST['titles']:
            qs = qs.exclude(title__icontains=title)

        if settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH:
            qs = qs.exclude(spam_status=1)

        return qs

    def _build_attributes(self):
        return dict(
            super(PreprintActionGenerator, self)._build_attributes(),
            preprint=self.preprint_query,
        )


class RegistrationActionGenerator(NodeActionGenerator):

    @property
    def category(self):
        return 'registration'

    @property
    def type(self):
        return 'registration'

    @property
    def retracted_query(self):
        return RawSQL(re.sub('\s+', ' ', '''COALESCE((
            WITH RECURSIVE ascendants AS (
                SELECT
                    N.id,
                    N.retraction_id
                FROM "{abstractnode}" AS N
                WHERE N.id = "{abstractnode}".id
            UNION ALL
                SELECT
                    N.id,
                    N.retraction_id
                FROM ascendants AS D
                    JOIN "{noderelation}" AS R ON R.child_id = D.id
                    JOIN "{abstractnode}" AS N ON N.id = R.parent_id
                WHERE D.retraction_id IS NULL AND R.is_node_link = FALSE
            ) SELECT
                RETRACTION.state = '{approved}' AS is_retracted
            FROM
                osf_retraction AS RETRACTION
            WHERE
                RETRACTION.id = (SELECT retraction_id FROM ascendants WHERE retraction_id IS NOT NULL LIMIT 1)
            LIMIT 1
        ), FALSE)'''.format(
            abstractnode=AbstractNode._meta.db_table,
            approved=models.Retraction.APPROVED,
            noderelation=NodeRelation._meta.db_table,
            retraction=models.Retraction._meta.db_table,
        )), [])

    def _get_queryset(self):
        qs = models.Registration.objects.annotate(
            has_qa_tags=Exists(AbstractNode.tags.through.objects.filter(
                abstractnode_id=OuterRef('pk'),
                tag__name__in=settings.DO_NOT_INDEX_LIST['tags'],
            )),
            is_archiving_or_failed=Exists(models.ArchiveJob.objects.filter(
                dst_node_id=OuterRef('pk'),
            ).exclude(
                status='SUCCESS'
            )),
        ).filter(
            is_public=True,
            is_deleted=False,
            is_archiving_or_failed=False,
            has_qa_tags=False,
        ).exclude(
            spam_status=2
        )
        for title in settings.DO_NOT_INDEX_LIST['titles']:
            qs = qs.exclude(title__icontains=title)

        if settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH:
            qs = qs.exclude(spam_status=1)

        return qs

    def _build_attributes(self):
        return dict(
            super(RegistrationActionGenerator, self)._build_attributes(),
            is_registration=Value(True),
            registered_date=F('registered_date'),
            is_retracted=self.retracted_query,
            registration_status=F('registration_approval__state')
        )

    def post_process(self, _id, doc):
        doc = super(RegistrationActionGenerator, self).post_process(_id, doc)

        if doc['is_retracted']:
            doc['wikis'] = {}

        doc['is_pending_registration'] = doc.pop('registration_status') == 'unapproved'

        return doc
