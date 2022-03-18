# -*- coding: utf-8 -*-
import logging
import json
import os

from addons.base.models import BaseUserSettings, BaseNodeSettings
from django.db import models
from osf.models.base import BaseModel
from osf.utils.fields import EncryptedTextField

logger = logging.getLogger(__name__)


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

    def get_file_metadatas(self):
        files = []
        for m in self.file_metadata.all():
            r = {
                'generated': False,
                'registered': m.registered,
                'path': m.path,
                'folder': m.folder,
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
            r['registered'] = False
            r['path'] = path
            return r
        m = q.first()
        r = {
            'generated': False,
            'registered': m.registered,
            'path': m.path,
            'folder': m.folder,
        }
        r.update(self._get_file_metadata(m))
        return r

    def set_file_metadata(self, filepath, file_metadata):
        self._validate_file_metadata(file_metadata)
        q = self.file_metadata.filter(path=filepath)
        if not q.exists():
            # TBD 親ファイルまたは子ファイルにすでにメタデータが付与されていたらエラー
            FileMetadata.objects.create(
                project=self,
                path=filepath,
                folder=file_metadata['folder'],
                registered=file_metadata['registered'],
                metadata=json.dumps({'items': file_metadata['items']})
            )
            return
        m = q.first()
        m.registered = file_metadata['registered']
        m.metadata = json.dumps({'items': file_metadata['items']})
        m.save()

    def delete_file_metadata(self, filepath):
        q = self.file_metadata.filter(path=filepath)
        if not q.exists():
            return
        q.first().delete()

    def get_project_metadata(self):
        if self.project_metadata is None or self.project_metadata == '':
            r = {}
        else:
            r = json.loads(self.project_metadata)
        r.update({
            'files': self.get_file_metadatas(),
        })
        return r

    def set_project_metadata(self, project_metadata):
        self._validate_project_metadata(project_metadata)
        files = project_metadata['files']
        del project_metadata['files']
        self.project_metadata = json.dumps(project_metadata)

        new_pathset = dict([(f['path'], f) for f in files])
        old_pathset = {}
        for m in self.file_metadata.all():
            old_pathset[m.path] = m
            if m.path not in new_pathset:
                m.delete()
                continue
            new_metadata = new_pathset[m.path]
            m.registered = new_metadata['registered']
            m.metadata = json.dumps({'items': new_metadata['items']})
            m.save()
        for path, f in new_pathset.items():
            if path in old_pathset:
                continue
            FileMetadata.objects.create(
                project=self,
                path=path,
                folder=f['folder'],
                metadata=json.dumps({'items': f['items']})
            )
        self.save()

    def _get_file_metadata(self, file_metadata):
        if file_metadata.metadata is None or file_metadata.metadata == '':
            return {}
        return json.loads(file_metadata.metadata)

    def _validate_file_metadata(self, file_metadata):
        if 'path' not in file_metadata:
            raise ValueError('Property "path" is not defined')
        if 'registered' not in file_metadata:
            raise ValueError('Property "registered" is not defined')
        if 'items' not in file_metadata:
            raise ValueError('Property "items" is not defined')

    def _validate_project_metadata(self, project_metadata):
        if 'type' not in project_metadata:
            raise ValueError('Property "type" is not defined')
        if 'items' not in project_metadata:
            raise ValueError('Property "items" is not defined')
        if 'files' not in project_metadata:
            raise ValueError('Property "files" is not defined')
        for f in project_metadata['files']:
            self._validate_file_metadata(f)


class FileMetadata(BaseModel):
    project = models.ForeignKey(NodeSettings, related_name='file_metadata',
                                db_index=True, null=True, blank=True,
                                on_delete=models.CASCADE)

    registered = models.BooleanField()

    folder = models.BooleanField()

    path = models.TextField()

    metadata = models.TextField(blank=True, null=True)
