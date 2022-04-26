# -*- coding: utf-8 -*-
import logging
import json
import os
import re

from addons.base.models import BaseUserSettings, BaseNodeSettings
from addons.osfstorage.models import OsfStorageFileNode
from django.db import models
from django.contrib.contenttypes.models import ContentType
from osf.models import DraftRegistration, BaseFileNode
from osf.models.base import BaseModel
from osf.models.metaschema import RegistrationSchema
from osf.utils.fields import EncryptedTextField

logger = logging.getLogger(__name__)


FIELD_GRDM_FILES = 'grdm-files'


def get_draft_files(draft_metadata):
    if FIELD_GRDM_FILES not in draft_metadata:
        return []
    draft_files = draft_metadata[FIELD_GRDM_FILES]
    if 'value' not in draft_files:
        return []
    draft_value = draft_files['value']
    if draft_value == '':
        return []
    return json.loads(draft_value)

def schema_has_field(schema, name):
    questions = sum([page['questions'] for page in schema['pages']], [])
    qids = [q['qid'] for q in questions]
    return name in qids


class ERadRecordSet(BaseModel):
    code = models.CharField(max_length=64, primary_key=True)

    def get_or_create_record(self, kenkyusha_no, kadai_id, nendo):
        objs = ERadRecord.objects.filter(
            recordset=self, kenkyusha_no=kenkyusha_no, kadai_id=kadai_id,
            nendo=nendo,
        )
        if objs.exists():
            return objs.first()
        return ERadRecord.objects.create(
            recordset=self, kenkyusha_no=kenkyusha_no, kadai_id=kadai_id,
            nendo=nendo,
        )

    @classmethod
    def get_or_create(cls, code):
        objs = cls.objects.filter(code=code)
        if objs.exists():
            return objs.first()
        return cls.objects.create(code=code)


class ERadRecord(BaseModel):
    recordset = models.ForeignKey(ERadRecordSet, related_name='records',
                                  db_index=True, null=True, blank=True,
                                  on_delete=models.CASCADE)

    kenkyusha_no = models.TextField(blank=True, null=True)
    kenkyusha_shimei = EncryptedTextField(blank=True, null=True)

    kenkyukikan_cd = models.TextField(blank=True, null=True)
    kenkyukikan_mei = models.TextField(blank=True, null=True)

    haibunkikan_cd = models.TextField(blank=True, null=True)
    haibunkikan_mei = models.TextField(blank=True, null=True)

    nendo = models.IntegerField(blank=True, null=True)

    seido_cd = models.TextField(blank=True, null=True)
    seido_mei = models.TextField(blank=True, null=True)

    jigyo_cd = models.TextField(blank=True, null=True)
    jigyo_mei = models.TextField(blank=True, null=True)

    kadai_id = models.TextField(blank=True, null=True)
    kadai_mei = EncryptedTextField(blank=True, null=True)

    bunya_cd = models.TextField(blank=True, null=True)
    bunya_mei = models.TextField(blank=True, null=True)


class RegistrationReportFormat(BaseModel):
    registration_schema_id = models.CharField(max_length=64, blank=True, null=True)

    name = models.TextField(blank=True, null=True)

    default_filename = models.TextField(blank=True, null=True)
    csv_template = models.TextField(blank=True, null=True)


class UserSettings(BaseUserSettings):
    """
    eRad KENKYUSHA_NO
    """
    erad_researcher_number = EncryptedTextField(blank=True, null=True)

    def get_erad_researcher_number(self):
        v = self.erad_researcher_number
        if v is not None and isinstance(v, bytes):
            return v.decode('utf8')
        return v

    def set_erad_researcher_number(self, erad_researcher_number):
        self.erad_researcher_number = erad_researcher_number
        self.save()


class NodeSettings(BaseNodeSettings):
    project_metadata = models.TextField(blank=True, null=True)

    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def complete(self):
        # Implementation for enumeration with <node_id>/addons API
        return True

    def get_file_metadatas(self):
        files = []
        for m in self.file_metadata.all():
            r = {
                'generated': False,
                'path': m.path,
                'hash': m.hash,
                'folder': m.folder,
                'urlpath': m.resolve_urlpath(),
            }
            r.update(self._get_file_metadata(m))
            files.append(r)
        return files

    def get_file_metadata_for_path(self, path):
        q = self.file_metadata.filter(path=path)
        if not q.exists():
            parent, _ = os.path.split(path.strip('/'))
            if len(parent) == 0:
                return None
            r = self.get_file_metadata_for_path(parent + '/')
            if r is None:
                return None
            r['generated'] = True
            r['hash'] = None
            r['path'] = path
            return r
        m = q.first()
        r = {
            'generated': False,
            'path': m.path,
            'folder': m.folder,
            'hash': m.hash,
            'urlpath': m.resolve_urlpath(),
        }
        r.update(self._get_file_metadata(m))
        return r

    def set_file_metadata(self, filepath, file_metadata):
        self._validate_file_metadata(file_metadata)
        q = self.file_metadata.filter(path=filepath)
        if not q.exists():
            FileMetadata.objects.create(
                project=self,
                path=filepath,
                hash=file_metadata['hash'],
                folder=file_metadata['folder'],
                metadata=json.dumps({'items': file_metadata['items']})
            )
            return
        m = q.first()
        m.hash = file_metadata['hash']
        m.metadata = json.dumps({'items': file_metadata['items']})
        for item in file_metadata['items']:
            if not item['active']:
                continue
            self._update_draft_files(
                item['schema'],
                filepath,
                item['data'])
        m.save()

    def set_file_hash(self, filepath, hash):
        q = self.file_metadata.filter(path=filepath)
        if not q.exists():
            return
        m = q.first()
        m.hash = hash
        m.save()

    def delete_file_metadata(self, filepath):
        q = self.file_metadata.filter(path=filepath)
        if not q.exists():
            return
        metadata = q.first()
        for schema in self._get_related_schemas(metadata.metadata):
            self._remove_draft_files(schema, filepath)
        metadata.delete()

    def get_project_metadata(self):
        if self.project_metadata is None or self.project_metadata == '':
            r = {}
        else:
            r = json.loads(self.project_metadata)
        r.update({
            'files': self.get_file_metadatas(),
        })
        return r

    def get_report_formats_for(self, schemas):
        formats = []
        for schema in schemas:
            for format in RegistrationReportFormat.objects.filter(registration_schema_id=schema._id):
                formats.append({
                    'schema_id': schema._id,
                    'name': format.name,
                })
        return {
            'formats': formats
        }

    def _get_file_metadata(self, file_metadata):
        if file_metadata.metadata is None or file_metadata.metadata == '':
            return {}
        return json.loads(file_metadata.metadata)

    def _validate_file_metadata(self, file_metadata):
        if 'path' not in file_metadata:
            raise ValueError('Property "path" is not defined')
        if 'folder' not in file_metadata:
            raise ValueError('Property "folder" is not defined')
        if 'hash' not in file_metadata:
            raise ValueError('Property "hash" is not defined')
        if 'items' not in file_metadata:
            raise ValueError('Property "items" is not defined')
        for i in file_metadata['items']:
            self._validate_file_metadata_item(i)

    def _validate_file_metadata_item(self, item):
        if 'active' not in item:
            raise ValueError('Property "active" is not defined')
        if 'schema' not in item:
            raise ValueError('Property "schema" is not defined')
        if 'data' not in item:
            raise ValueError('Property "data" is not defined')

    def _update_draft_files(self, schema, filepath, metadata):
        drafts = self._get_registration_schema(schema)
        for draft in drafts:
            draft_schema = draft.registration_schema.schema
            if not schema_has_field(draft_schema, FIELD_GRDM_FILES):
                raise ValueError('Schema has no grdm-files field')
            draft_metadata = draft.registration_metadata
            draft_files = get_draft_files(draft_metadata)
            for draft_file in draft_files:
                if draft_file['path'] != filepath:
                    continue
                draft_file['metadata'] = metadata
            draft.update_metadata({
                FIELD_GRDM_FILES: {
                    'value': json.dumps(draft_files, indent=2),
                },
            })
            draft.save()

    def _remove_draft_files(self, schema, filepath):
        drafts = self._get_registration_schema(schema)
        for draft in drafts:
            draft_schema = draft.registration_schema.schema
            if not schema_has_field(draft_schema, FIELD_GRDM_FILES):
                raise ValueError('Schema has no grdm-files field')
            draft_metadata = draft.registration_metadata
            draft_files = get_draft_files(draft_metadata)
            draft_files = [draft_file
                           for draft_file in draft_files
                           if draft_file['path'] != filepath]
            draft.update_metadata({
                FIELD_GRDM_FILES: {
                    'value': json.dumps(draft_files, indent=2),
                },
            })
            draft.save()

    def _get_related_schemas(self, metadata):
        if metadata is None or len(metadata) == 0:
            return []
        metadataobj = json.loads(metadata)
        if 'items' not in metadataobj:
            return []
        return [i['schema'] for i in metadataobj['items']]

    def _get_registration_schema(self, schema):
        try:
            registration_schema = RegistrationSchema.objects.get(_id=schema)
            drafts = DraftRegistration.objects.filter(
                branched_from=self.owner,
                registration_schema=registration_schema
            )
            return drafts
        except RegistrationSchema.DoesNotExist:
            return []


class FileMetadata(BaseModel):
    project = models.ForeignKey(NodeSettings, related_name='file_metadata',
                                db_index=True, null=True, blank=True,
                                on_delete=models.CASCADE)

    folder = models.BooleanField()

    path = models.TextField()

    hash = models.CharField(max_length=128, blank=True, null=True)

    metadata = models.TextField(blank=True, null=True)

    def resolve_urlpath(self):
        node = self.project.owner
        if self.folder:
            return node.url + 'files/dir/' + self.path
        m = re.match(r'([^\/]+)(/.*)', self.path)
        if not m:
            raise ValueError('Malformed path: ' + self.path)
        provider = m.group(1)
        path = m.group(2)
        if provider == 'osfstorage':
            # materialized path -> object path
            content_type = ContentType.objects.get_for_model(node)
            filenode = [fn for fn in OsfStorageFileNode.objects.filter(target_content_type=content_type) if fn.materialized_path == path]
            if len(filenode) == 0:
                logger.warn('No files: ' + self.path)
                return None
            path = filenode[0].path
        file_guids = BaseFileNode.resolve_class(provider, BaseFileNode.FILE).get_file_guids(
            materialized_path=path,
            provider=provider,
            target=node
        )
        if len(file_guids) == 0:
            fileUrl = node.url + 'files/' + provider + path
            logger.info('No guid: ' + self.path + '(provider=' + provider + ')')
            return fileUrl
        return '/' + file_guids[0] + '/'
