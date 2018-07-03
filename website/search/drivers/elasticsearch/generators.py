from __future__ import absolute_import
from __future__ import unicode_literals

import abc
import logging
import re
import uuid

from django.contrib.postgres.fields import JSONField
from django.db import connection
from django.db import transaction
from django.db.models import Case, Exists, F, OuterRef, Subquery, Value, When
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce, Concat
from django.utils.functional import cached_property

from addons.wiki.models import WikiPage, WikiVersion

from osf import models
from osf.expressions import JSONBuildObject, ArrayAgg, JSONAgg
from osf.utils.workflows import DefaultStates

from website import settings


logger = logging.getLogger(__name__)


class AbstractActionGenerator(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def type(self):
        raise NotImplementedError

    @abc.abstractproperty
    def model(self):
        raise NotImplementedError

    @property
    def inital_queryset(self):
        if self._initial_query:
            return self.model.objects.filter(**self._initial_query)
        return self.model.objects.all()

    def __init__(self, index, doc_type, initial_query=None, chunk_size=1000):
        self._index = index
        self._doc_type = doc_type
        self._chunk_size = chunk_size
        self._remove = bool(initial_query)
        self._initial_query = initial_query or {}

    @abc.abstractmethod
    def build_query(self):
        raise NotImplementedError()

    def post_process(self, _id, doc):
        return doc

    def guid_for(self, model, ref='pk'):
        return Subquery(
            models.Guid.objects.filter(
                object_id=OuterRef(ref),
                content_type__app_label=model._meta.app_label,
                content_type__model=model._meta.concrete_model._meta.model_name,
            ).values('_id')[:1]
        )

    def _fetch_docs(self, query):
        with connection.cursor() as cursor:
            cursor_id = str(uuid.uuid4())
            query, params = query.query.sql_with_params()

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
                    yield row[0]

    def __iter__(self):
        with transaction.atomic():
            to_remove = []
            qs = self.build_query()

            for doc in self._fetch_docs(qs):
                _id = doc.pop('_id')
                doc['id'] = _id  # For backwards compat
                doc['type'] = self.type  # doc_types no longer exist so we have to do it ourselves
                _source = self.post_process(_id, doc)

                # This is only here for collection submissions at the moment
                # it should be removed whenever that issue is fixed/handled
                if not _source:
                    to_remove.append(_id)
                    continue

                yield {
                    '_id': _id,
                    '_o[_type': 'index',
                    '_index': self._index,
                    '_type': self._doc_type,
                    '_source': _source,
                }

            if not self._remove:
                return

            for _id in to_remove:
                yield {
                    '_id': _id,
                    '_op_type': 'delete',
                    '_index': self._index,
                    '_type': self._doc_type,
                }

            # Probably a better way to do this
            # but we want to steal the doc annotation (and any others it might use)
            # The problem being that resolve_expression has already been called on the
            # annotation, so our new queryset won't have any of the joins required.
            # Clone it, knock off the filters, and combine with our query to get all the joins
            remove_qs = qs._clone()
            remove_qs.query.where.children = []

            # remove_qs.filter(**self._initial_query)

            # remove_qs = self.inital_queryset
            # remove_qs.query.combine(clone.query, AND)

            # This was an after thought, in case you couldn't tell
            # It's a bit wasteful to generate the entire document here but
            # _id needs to be formatted the same way everytime so there's not much of a choice
            remove_qs = remove_qs.values('id').filter(
                **self._initial_query
            ).annotate(
                **qs.query.annotation_select
            ).exclude(
                id__in=qs.values('id')
            ).values('doc')

            for doc in self._fetch_docs(remove_qs):
                yield {
                    '_id': doc['_id'],
                    '_op_type': 'delete',
                    '_index': self._index,
                    '_type': self._doc_type,
                }


class FileActionGenerator(AbstractActionGenerator):
    type = 'file'
    model = models.BaseFileNode

    @cached_property
    def tags_query(self):
        return Coalesce(Subquery(
            models.BaseFileNode.tags.through.objects.filter(
                basefilenode_id=OuterRef('pk')
            ).annotate(
                tags=ArrayAgg(F('tag__name'))
            ).values('tags')
        ), [])

    @cached_property
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
            abstractnode=models.AbstractNode._meta.db_table,
            approved=models.Retraction.APPROVED,
            noderelation=models.NodeRelation._meta.db_table,
            retraction=models.Retraction._meta.db_table,
        )), [])

    @cached_property
    def node_query(self):
        return JSONBuildObject(
            title=F('node__title'),
            guid=self.guid_for(models.AbstractNode, 'node__pk'),
            type=F('node__type'),
            is_retracted=Coalesce(self.retracted_query, Value(False)),
            parent_guid=Subquery(
                models.NodeRelation.objects.filter(
                    is_node_link=False,
                    child_id=OuterRef('node__pk')
                ).annotate(
                    guid=self.guid_for(models.AbstractNode, 'parent_id')
                ).order_by('created').values('guid')[:1]
            )
        )

    def build_query(self):
        qs = self.inital_queryset

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
                guid=self.guid_for(models.BaseFileNode),
                name=F('name'),
                category=Value('file'),
                tags=self.tags_query,
                node=self.node_query,
            ),
            file_qa_tags=Exists(models.BaseFileNode.tags.through.objects.filter(
                basefilenode_id=OuterRef('pk'),
                tag__name__in=settings.DO_NOT_INDEX_LIST['tags'],
            )),
            node_qa_tags=Exists(models.AbstractNode.tags.through.objects.filter(
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
        ).exclude(
            # Exclude quickfiles that do not have an active user
            # IE spam users
            node__creator__is_active=False,
            node__type=models.QuickFilesNode._meta.label_lower,
        ).values('doc')

    def post_process(self, _id, doc):
        node = doc.pop('node')
        guid = doc.pop('guid', None)

        extra = doc['name'].replace('_', ' ').replace('-', ' ').replace('.', ' ')
        if extra == doc['name']:
            extra = ''

        doc.update({
            'deep_url': '/{}/files/osfstorage/{}/'.format(node['guid'], _id),
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
    type = 'institution'
    model = models.Institution

    def build_query(self):
        return models.Institution.objects.annotate(
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


class CollectionSubmission(AbstractActionGenerator):
    type = 'collectionSubmission'
    model = models.CollectedGuidMetadata

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
        # TODO This might be better as a union all in the future
        # Provided that nested GFKs can be joined on
        return models.CollectedGuidMetadata.objects.filter(
            collection__deleted__isnull=True,
            collection__is_bookmark_collection=False,
            collection__is_public=True,
            collection__provider__isnull=False,
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
                node=Case(
                    When(
                        guid__content_type__model=models.AbstractNode._meta.model_name,
                        guid__content_type__app_label=models.AbstractNode._meta.app_label,
                        then=Subquery(
                            models.Guid.objects.degeneric(referent=models.AbstractNode).filter(
                                pk=OuterRef('guid__id'),
                                referent__is_public=True,
                                referent__is_deleted=False,
                            ).annotate(
                                doc=JSONBuildObject(
                                    guid=F('_id'),
                                    title=F('referent__title'),
                                    description=F('referent__description'),
                                    contributors=self.contributors_query,
                                )
                            ).values('doc')
                        )
                    ),
                    default=Value(None),
                    output_field=JSONField(),
                ),
            )
        ).values('doc')

    def post_process(self, _id, doc):
        node = doc.pop('node')

        if node:
            doc['title'] = node['title']
            doc['abstract'] = node['description']
            doc['url'] = '/{}/'.format(node['guid'])

            doc['contributors'] = [{
                'fullname': contrib['fullname'],
                'url': '/{}/'.format(contrib['guid']) if contrib['is_active'] else None
            } for contrib in node['contributors']]
        else:
            # This could be avoided using the union all strategy
            logger.warning('No Collected Object present on {}'.format(_id))
            return None

        return doc


class UserActionGenerator(AbstractActionGenerator):
    type = 'user'
    model = models.OSFUser

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
                key: models.OSFUser.SOCIAL_FIELDS[key].format(val)
                if isinstance(val, basestring) else val
                for key, val in (doc.pop('social') or {}).items()
                if val and key in models.OSFUser.SOCIAL_FIELDS
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
            models.AbstractNode.tags.through.objects.filter(
                tag__system=False,
                abstractnode_id=OuterRef('pk')
            ).annotate(
                tags=ArrayAgg(F('tag__name'))
            ).values('tags')
        ), [])

    @property
    def affiliated_institutions_query(self):
        return Coalesce(Subquery(
            models.Node.affiliated_institutions.through.objects.filter(
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
                            then=Concat(Value('/'), self.guid_for(models.OSFUser, 'user__pk'), Value('/'))
                        ),
                        default=Value(None)
                    )
                ), order_by=F('_order').asc()),
            ).order_by().values('doc')
        )

    @property
    def parent_query(self):
        return Subquery(
            models.NodeRelation.objects.filter(
                is_node_link=False,
                child_id=OuterRef('pk')
            ).annotate(
                guid=self.guid_for(models.AbstractNode, 'parent_id')
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
            nodelicense=models.NodeLicense._meta.db_table,
            noderelation=models.NodeRelation._meta.db_table,
            abstractnode=models.AbstractNode._meta.db_table,
            nodelicenserecord=models.NodeLicenseRecord._meta.db_table
        )), [])

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
            '_id': self.guid_for(models.AbstractNode),
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
    type = 'project'
    category = 'project'
    model = models.AbstractNode

    def _get_queryset(self):
        qs = self.inital_queryset.annotate(
            has_parent=Exists(models.NodeRelation.objects.filter(child_id=OuterRef('pk'), is_node_link=False)),
            has_qa_tags=Exists(models.AbstractNode.tags.through.objects.filter(
                abstractnode_id=OuterRef('pk'),
                tag__name__in=settings.DO_NOT_INDEX_LIST['tags'],
            )),
            has_preprint=Exists(models.PreprintService.objects.filter(
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
    type = 'component'
    category = 'component'
    model = models.Node

    def _get_queryset(self):
        qs = self.inital_queryset.annotate(
            has_parent=Exists(models.NodeRelation.objects.filter(child_id=OuterRef('pk'), is_node_link=False)),
            has_qa_tags=Exists(models.AbstractNode.tags.through.objects.filter(
                abstractnode_id=OuterRef('pk'),
                tag__name__in=settings.DO_NOT_INDEX_LIST['tags'],
            )),
            has_preprint=Exists(models.PreprintService.objects.filter(
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
    type = 'preprint'
    category = 'preprint'
    model = models.Node

    @property
    def preprint_query(self):
        return Subquery(models.PreprintService.objects.annotate(
            doc=JSONBuildObject(
                guid=self.guid_for(models.PreprintService),
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
        qs = self.inital_queryset.annotate(
            has_qa_tags=Exists(models.AbstractNode.tags.through.objects.filter(
                abstractnode_id=OuterRef('pk'),
                tag__name__in=settings.DO_NOT_INDEX_LIST['tags'],
            )),
            has_preprint=Exists(models.PreprintService.objects.filter(
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
    type = 'registration'
    category = 'registration'
    model = models.Registration

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
            abstractnode=models.AbstractNode._meta.db_table,
            approved=models.Retraction.APPROVED,
            noderelation=models.NodeRelation._meta.db_table,
            retraction=models.Retraction._meta.db_table,
        )), [])

    def _get_queryset(self):
        qs = self.inital_queryset.annotate(
            has_qa_tags=Exists(models.AbstractNode.tags.through.objects.filter(
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
