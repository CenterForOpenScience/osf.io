import datetime
import urlparse

from modularodm import fields, Q

from framework.encryption import EncryptedStringField
from framework.celery_tasks.handlers import enqueue_task
from framework.exceptions import PermissionsError
from framework.guid.model import GuidStoredObject
from framework.mongo import ObjectId, StoredObject
from framework.mongo.utils import unique_on
from website.files.models import StoredFileNode
from website.preprints.tasks import on_preprint_updated
from website.project.model import NodeLog
from website.project.licenses import set_license
from website.project.taxonomies import Subject, validate_subject_hierarchy
from website.util import api_v2_url
from website.util.permissions import ADMIN
from website import settings


@unique_on(['node', 'provider'])
class PreprintService(GuidStoredObject):

    _id = fields.StringField(primary=True)
    date_created = fields.DateTimeField(auto_now_add=True)
    date_modified = fields.DateTimeField(auto_now=True)
    provider = fields.ForeignField('PreprintProvider', index=True)
    node = fields.ForeignField('Node', index=True)
    is_published = fields.BooleanField(default=False, index=True)
    date_published = fields.DateTimeField()
    license = fields.ForeignField('NodeLicenseRecord')

    # This is a list of tuples of Subject id's. MODM doesn't do schema
    # validation for DictionaryFields, but would unsuccessfully attempt
    # to validate the schema for a list of lists of ForeignFields.
    #
    # Format: [[root_subject._id, ..., child_subject._id], ...]
    subjects = fields.DictionaryField(list=True)

    @property
    def primary_file(self):
        if not self.node:
            return
        return self.node.preprint_file

    @property
    def article_doi(self):
        if not self.node:
            return
        return self.node.preprint_article_doi

    @property
    def is_preprint_orphan(self):
        if not self.node:
            return
        return self.node.is_preprint_orphan

    @property
    def deep_url(self):
        # Required for GUID routing
        return '/preprints/{}/'.format(self._primary_key)

    @property
    def url(self):
        if self.provider._id != 'osf':
            # Note that this will change with Phase 2 of branded preprints.
            return '/preprints/{}/{}/'.format(self.provider._id, self._id)

        return '/{}/'.format(self._id)

    @property
    def absolute_url(self):
        return urlparse.urljoin(settings.DOMAIN, self.url)

    @property
    def absolute_api_v2_url(self):
        path = '/preprints/{}/'.format(self._id)
        return api_v2_url(path)

    def has_permission(self, *args, **kwargs):
        return self.node.has_permission(*args, **kwargs)

    def get_subjects(self):
        ret = []
        for subj_list in self.subjects:
            subj_hierarchy = []
            for subj_id in subj_list:
                subj = Subject.load(subj_id)
                if subj:
                    subj_hierarchy += ({'id': subj_id, 'text': subj.text}, )
            if subj_hierarchy:
                ret.append(subj_hierarchy)
        return ret

    def set_subjects(self, preprint_subjects, auth, save=False):
        if not self.node.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can change a preprint\'s subjects.')

        self.subjects = []
        for subj_list in preprint_subjects:
            subj_hierarchy = []
            for s in subj_list:
                subj_hierarchy.append(s)
            if subj_hierarchy:
                validate_subject_hierarchy(subj_hierarchy)
                self.subjects.append(subj_hierarchy)

        if save:
            self.save()

    def set_primary_file(self, preprint_file, auth, save=False):
        if not self.node.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can change a preprint\'s primary file.')

        if not isinstance(preprint_file, StoredFileNode):
            preprint_file = preprint_file.stored_object

        if preprint_file.node != self.node or preprint_file.provider != 'osfstorage':
            raise ValueError('This file is not a valid primary file for this preprint.')

        existing_file = self.node.preprint_file
        self.node.preprint_file = preprint_file

        # only log if updating the preprint file, not adding for the first time
        if existing_file:
            self.node.add_log(
                action=NodeLog.PREPRINT_FILE_UPDATED,
                params={
                    'preprint': self._id
                },
                auth=auth,
                save=False
            )

        if save:
            self.save()
            self.node.save()

    def set_published(self, published, auth, save=False):
        if not self.node.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can publish a preprint.')

        if self.is_published and not published:
            raise ValueError('Cannot unpublish preprint.')

        self.is_published = published

        if published:
            if not (self.node.preprint_file and self.node.preprint_file.node == self.node):
                raise ValueError('Preprint node is not a valid preprint; cannot publish.')
            if not self.provider:
                raise ValueError('Preprint provider not specified; cannot publish.')
            if not self.subjects:
                raise ValueError('Preprint must have at least one subject to be published.')
            self.date_published = datetime.datetime.utcnow()
            self.node._has_abandoned_preprint = False

            self.node.add_log(
                action=NodeLog.PREPRINT_INITIATED,
                params={
                    'preprint': self._id
                },
                auth=auth,
                save=False,
            )

            if not self.node.is_public:
                self.node.set_privacy(
                    self.node.PUBLIC,
                    auth=None,
                    log=True
                )

        if save:
            self.node.save()
            self.save()

    def set_preprint_license(self, license_detail, auth, save=False):

        set_license(self, license_detail, auth, node_type='preprint')

        self.node.add_log(
            action=NodeLog.PREPRINT_LICENSE_UPDATED,
            params={
                'preprint': self._id
            },
            auth=auth,
            save=False
        )

        if save:
            self.save()

    def save(self, *args, **kwargs):
        saved_fields = super(PreprintService, self).save(*args, **kwargs)
        if saved_fields:
            enqueue_task(on_preprint_updated.s(self._id))


class PreprintProvider(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    name = fields.StringField(required=True)
    logo_name = fields.StringField()
    header_text = fields.StringField()
    description = fields.StringField()
    banner_name = fields.StringField()
    external_url = fields.StringField()
    email_contact = fields.StringField()
    email_support = fields.StringField()
    access_token = EncryptedStringField()
    advisory_board = fields.StringField()
    social_twitter = fields.StringField()
    social_facebook = fields.StringField()
    social_instagram = fields.StringField()
    subjects_acceptable = fields.DictionaryField(list=True, default=lambda: [])
    licenses_acceptable = fields.ForeignField('NodeLicense', list=True, default=lambda: [])

    @property
    def top_level_subjects(self):
        if len(self.subjects_acceptable) == 0:
            return Subject.find(Q('parents', 'eq', []))
        tops = set([sub[0][0] for sub in self.subjects_acceptable])
        return [Subject.load(sub) for sub in tops]

    @property
    def all_subjects(self):
        q = []
        for rule in self.subjects_acceptable:
            if rule[1]:
                q.append(Q('parents', 'eq', Subject.load(rule[0][-1])))
                if len(rule[0]) == 1:
                    potential_parents = Subject.find(Q('parents', 'eq', Subject.load(rule[0][-1])))
                    for parent in potential_parents:
                        q.append(Q('parents', 'eq', parent))
            for sub in rule[0]:
                q.append(Q('_id', 'eq', sub))
        return Subject.find(reduce(lambda x, y: x | y, q)) if len(q) > 1 else (Subject.find(q[0]) if len(q) else Subject.find())

    def get_absolute_url(self):
        return '{}preprint_providers/{}'.format(self.absolute_api_v2_url, self._id)

    @property
    def absolute_api_v2_url(self):
        path = '/preprint_providers/{}/'.format(self._id)
        return api_v2_url(path)

    @property
    def logo_path(self):
        if self.logo_name:
            return '/static/img/preprint_providers/{}'.format(self.logo_name)
        else:
            return None

    @property
    def banner_path(self):
        if self.logo_name:
            return '/static/img/preprint_providers/{}'.format(self.logo_name)
        else:
            return None
