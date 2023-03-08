from datetime import datetime
import html
import io
import json
import logging
import os
import re
import shutil
import tempfile
from future.moves.urllib.parse import urljoin
from zipfile import ZipFile

import furl
from django.contrib.contenttypes.models import ContentType
from rocrate.rocrate import ROCrate
from rocrate.model.person import Person
from rocrate.model.contextentity import ContextEntity
from rocrate.model.data_entity import DataEntity
from rest_framework import status as http_status
import requests
import zipfly

from api.nodes.serializers import NodeSerializer
from api.base.utils import waterbutler_api_url_for
from framework.auth import Auth
from framework.celery_tasks import app as celery_app
from framework.exceptions import HTTPError, PermissionsError
from osf.models import Guid, OSFUser, AbstractNode, Comment, BaseFileNode, DraftRegistration, Registration
from website.util import waterbutler
from website import settings as website_settings
from osf.models.metaschema import RegistrationSchema
from . import SHORT_NAME, settings
from .jsonld import (
    convert_file_metadata_to_json_ld_entities,
    convert_project_metadata_to_json_ld_entities,
    convert_json_ld_entity_to_file_metadata_item,
)
from addons.wiki.models import WikiPage
from addons.metadata.apps import SHORT_NAME as METADATA_SHORT_NAME


logger = logging.getLogger(__name__)

EXPORT_REGISTRATION_SCHEMA_NAME = '公的資金による研究データのメタデータ登録'
DEFAULT_ADDONS_FILES = [{
    'materialized': '/.weko/',
    'enable': False,
}]


class RequestWrapper(object):
    def __init__(self, auth):
        self.auth = auth

    @property
    def user(self):
        logger.info(f'USER: {self.auth.user}')
        return self.auth.user

    @property
    def method(self):
        return 'PUT'

    @property
    def GET(self):
        return {}

class WaterButlerClient(object):
    def __init__(self, user):
        self.user = user

    def get_client_for_node(self, node):
        return WaterButlerClientForNode(self.user, node)

class WaterButlerClientForNode(object):
    def __init__(self, user, node):
        self.cookie = user.get_or_create_cookie().decode()
        self.node = node

    def get_root_files(self, name):
        response = requests.get(
            waterbutler_api_url_for(
                self.node._id, name, path='/', _internal=True, meta=''
            ),
            headers={'content-type': 'application/json'},
            cookies={website_settings.COOKIE_NAME: self.cookie}
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()['data']
        return [WaterButlerObject(file, self) for file in data]

    def create_root_folder(self, provider, folder_name):
        resp = waterbutler.create_folder(
            self.cookie, self.node._id, folder_name, f'{provider}/',
        )
        data = resp.json()
        return WaterButlerObject(data, self)

    def upload_root_file(self, file, file_name, provider):
        resp = waterbutler.upload_file(self.cookie, self.node._id, file, file_name, provider)
        data = resp.json()['data']
        return WaterButlerObject(data, self)

    def get_file_by_materialized_path(self, path, create=False):
        logger.debug(f'Search: {path}')
        path_segments = path.split('/')
        folder = path_segments[-1] == ''
        if folder:
            path_segments = path_segments[:-1]
        if len(path_segments) == 0:
            raise IOError('Empty path')
        if len(path_segments) == 1:
            return WaterButlerProvider(path_segments[0], self)
        if len(path_segments) == 2:
            provider = path_segments[0]
            target_path = '/'.join(path_segments[1:])
            if folder:
                target_path += '/'
            logger.debug(f'Fetching... provider={provider}, path={target_path}')
            files = self.get_root_files(provider)
            logger.debug(f'Fetched: provider={provider}, path={target_path}, files={files}')
            candidates = [
                file
                for file in files
                if 'materialized' in file.attributes and file.attributes['materialized'] == f'/{target_path}'
            ]
            if create and len(candidates) == 0:
                return self.create_root_folder(provider, path_segments[1])
            return candidates[0] if len(candidates) else None
        parent_path = '/'.join(path_segments[:-1]) + '/'
        parent_file = self.get_file_by_materialized_path(parent_path, create=create)
        target_path = '/'.join(path_segments[1:])
        if folder:
            target_path += '/'
        logger.debug(f'Fetching... path={target_path}')
        files = parent_file.get_files()
        logger.debug(f'Fetched: path={target_path}, files={files}')
        candidates = [
            file
            for file in files
            if 'materialized' in file.attributes and file.attributes['materialized'] == f'/{target_path}'
        ]
        if create and len(candidates) == 0:
            return parent_file.create_folder(path_segments[-1])
        return candidates[0] if len(candidates) else None

class WaterButlerProvider(object):
    def __init__(self, provider, wb):
        self.provider = provider
        self.wb = wb
        self._children = {}

    def get_files(self):
        return self.wb.get_root_files(self.provider)

    def create_folder(self, folder_name):
        return self.wb.create_root_folder(self.provider, folder_name)

    def upload_file(self, file, file_name):
        return self.wb.upload_root_file(file, file_name, self.provider)

class WaterButlerObject(object):
    def __init__(self, resp, wb):
        self.raw = resp
        self.wb = wb
        self._children = {}

    def get_files(self):
        logger.debug(f'list files: {self.links}')
        url = furl.furl(website_settings.WATERBUTLER_INTERNAL_URL)
        file_url = furl.furl(self.links['new_folder'])
        url.path = str(file_url.path)
        response = requests.get(
            url.url,
            headers={'content-type': 'application/json'},
            cookies={website_settings.COOKIE_NAME: self.wb.cookie}
        )
        response.raise_for_status()
        return [WaterButlerObject(f, self.wb) for f in response.json()['data']]

    def download_to(self, f):
        logger.debug(f'download content: {self.links}')
        url = furl.furl(website_settings.WATERBUTLER_INTERNAL_URL)
        file_url = furl.furl(self.links['download'])
        url.path = str(file_url.path)
        response = requests.get(
            url.url,
            headers={'content-type': 'application/json'},
            cookies={website_settings.COOKIE_NAME: self.wb.cookie},
            stream=True,
        )
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    def delete(self):
        url = furl.furl(website_settings.WATERBUTLER_INTERNAL_URL)
        file_url = furl.furl(self.links['delete'])
        url.path = str(file_url.path)
        response = requests.delete(
            url.url,
            headers={'content-type': 'application/json'},
            cookies={website_settings.COOKIE_NAME: self.wb.cookie},
        )
        response.raise_for_status()

    def create_folder(self, folder_name):
        provider = self.raw['attributes']['provider']
        path = self.raw['attributes']['path']
        resp = waterbutler.create_folder(
            self.wb.cookie, self.wb.node._id, folder_name,
            provider + path,
        )
        data = resp.json()
        return WaterButlerObject(data, self.wb)

    def upload_file(self, file, file_name):
        provider = self.raw['attributes']['provider']
        path = self.raw['attributes']['path']
        resp = waterbutler.upload_file(
            self.wb.cookie, self.wb.node._id, file, file_name,
            provider + path,
        )
        data = resp.json()['data']
        return WaterButlerObject(data, self.wb)

    @property
    def guid(self):
        return self.raw['id']

    @property
    def attributes(self):
        return self.raw['attributes']

    @property
    def links(self):
        return self.raw['links']

    def __getattr__(self, name):
        attr = self.raw['attributes']
        if name in attr:
            return attr[name]
        raise AttributeError(name)

class GeneratorIOStream(io.RawIOBase):

    def __init__(self, iter):
        self._iter = iter
        self._left = b''

    def _read1(self, size=None):
        while not self._left:
            try:
                self._left = next(self._iter)
            except StopIteration:
                break
        ret = self._left[:size]
        self._left = self._left[len(ret):]
        return ret

    def readall(self):
        r = []
        while True:
            m = self._read1()
            if not m:
                break
            r.append(m)
        return b''.join(r)

    def readinto(self, b):
        pos = 0
        while pos < len(b):
            n = len(b) - pos
            m = self._read1(n)
            if not m:
                break
            for i, v in enumerate(m):
                b[pos + i] = v
            pos += len(m)
        return pos

def _as_web_file(node, wb_file):
    if wb_file.provider == 'osfstorage':
        file_id = re.match(r'^/([^/]+)$', wb_file.path).group(1)
        logger.debug(f'web_file({wb_file.path}): {file_id}')
        return BaseFileNode.objects.filter(
            _id=file_id,
            provider=wb_file.provider,
            target_object_id=node.id,
            deleted__isnull=True,
            target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
        ).first()
    return BaseFileNode.objects.filter(
        _path=wb_file.path,
        provider=wb_file.provider,
        target_object_id=node.id,
        deleted__isnull=True,
        target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
    ).order_by('-id').first()

class BaseROCrateFactory(object):

    def __init__(self, node, work_dir):
        self.node = node
        self.work_dir = work_dir
        self.include_users = False

    def _build_ro_crate_as_json(self):
        crate = ROCrate()
        extra_contexts = [
            'https://w3id.org/ro/terms/workflow-run',
            'https://purl.org/gakunin-rdm/project/0.1',
        ]
        crate, files = self._build_ro_crate(crate)
        metadata_file = os.path.join(self.work_dir, 'ro-crate-metadata.json')
        zip_path = os.path.join(self.work_dir, 'work.zip')
        crate.write_zip(zip_path)
        with ZipFile(zip_path, 'r') as zf:
            with zf.open('ro-crate-metadata.json') as f:
                metadata = json.load(f)
                metadata['@context'] = [
                    metadata['@context'],
                ] + extra_contexts
                with open(metadata_file, 'w') as df:
                    df.write(json.dumps(metadata))
        return metadata_file, files

    def _ro_crate_path_list(self):
        metadata_file, files = self._build_ro_crate_as_json()
        yield {
            'fs': metadata_file,
            'n': 'ro-crate-metadata.json',
        }
        tmp_path = os.path.join(self.work_dir, 'temp.dat')
        total_size = 0
        for path, file, _ in files:
            logger.info(f'Downloading... {path}, size={file.size}')
            assert path.startswith('./'), path
            self._check_file_size(total_size + int(file.size))
            with open(tmp_path, 'wb') as df:
                file.download_to(df)
            size = os.path.getsize(tmp_path)
            if size != int(file.size):
                raise IOError(f'File size mismatch: {size} != {file.size}')
            total_size += size
            logger.info(f'Downloaded: path={path}, size={size} (total downloaded={total_size})')
            yield {
                'fs': tmp_path,
                'n': path[2:],
            }

    def _check_file_size(self, total_size):
        if total_size <= settings.MAX_EXPORTABLE_FILES_BYTES:
            return
        params = f'exported={total_size}, limit={settings.MAX_EXPORTABLE_FILES_BYTES}'
        raise IOError(f'Exported file size exceeded limit: {params}')

    def _build_ro_crate(self, crate):
        raise NotImplementedError()

    def get_ro_crate_json(self):
        json_file, _ = self._build_ro_crate_as_json()
        with open(json_file, 'r') as f:
            return json.load(f)

    def download_to(self, zip_path):
        zfly = zipfly.ZipFly(paths=self._ro_crate_path_list())
        with open(zip_path, 'wb') as f:
            shutil.copyfileobj(GeneratorIOStream(zfly.generator()), f)
        logger.debug(f'Downloaded: {os.path.getsize(zip_path)}')

    def _is_file_archivable(self, wb_file):
        return True

    def _create_file_entities(self, crate, node, base_path, wb_file, user_ids, schema_ids, comment_ids):
        path = os.path.join(base_path, wb_file.name)
        if not self._is_file_archivable(wb_file):
            logger.info(f'File is not target: {path}')
            return None, []
        r = []
        entity = None
        if wb_file.attributes['kind'] == 'folder':
            path += '/'
            wb_files = wb_file.get_files()
            for child in wb_files:
                _, children = self._create_file_entities(crate, node, path, child, user_ids, schema_ids, comment_ids)
                r += children
            entity = crate.add(DataEntity(crate, path, properties={
                '@type': 'RDMFolder',
                'name': wb_file.name,
                'hasPart': [
                    {'@id': f'{path}{child.name}/' if child.attributes['kind'] == 'folder' else f'{path[2:]}{child.name}'}
                    for child in wb_files
                ]
            }))
        else:
            web_file = _as_web_file(self.node, wb_file)
            comments = []
            tags = []
            creator = None
            custom_props = {}
            if web_file is not None:
                latest = web_file.versions.order_by('-created').first()
                custom_props['rdmURL'] = urljoin(
                    website_settings.DOMAIN,
                    web_file.get_guid(create=True)._id,
                )
                if latest is not None:
                    creator = latest.creator
                    custom_props['version'] = latest.identifier
                    logger.debug(f'FileVersion Metadata: {latest.metadata}')
                    for hash in ['md5', 'sha1', 'sha256', 'sha512']:
                        if hash not in latest.metadata:
                            continue
                        custom_props[hash] = latest.metadata[hash]
                if self.include_users and creator._id not in user_ids:
                    crate.add(*self._create_contributor_entities(crate, creator, user_ids))
                comments = sum([
                    self._create_comment_entities(crate, path, None, c, user_ids, comment_ids)
                    for c in Comment.objects.filter(root_target=web_file.get_guid(), deleted__isnull=True)
                ], [])
                tags += [t.name for t in web_file.tags.all()]
            r.append((path, wb_file, comments))
            props = {
                'name': wb_file.name,
                'encodingFormat': wb_file.contentType,
                'contentSize': str(wb_file.size),
                'dateModified': wb_file.modified_utc,
                'dateCreated': wb_file.created_utc,
                'keywords': tags,
            }
            props.update(custom_props)
            if creator is not None and creator._id in user_ids:
                props['creator'] = {
                    '@id': user_ids[creator._id],
                }
            entity = crate.add_file(path, dest_path=path, properties=props)
        self._create_file_metadata_entities(crate, node, path, self._get_materialized_path(wb_file), schema_ids)
        return entity, r

    def _get_materialized_path(self, wb_file):
        if 'materialized' not in wb_file.attributes:
            raise ValueError('Materialized path not defined')
        return wb_file.attributes['provider'] + wb_file.attributes['materialized']

    def _create_project_entities(self, crate, entity_id, node, user_ids, extra_props=None):
        props = {
            '@type': 'RDMProject',
            'name': node.title,
            'description': node.description,
            'category': node.category,
            'dateCreated': _to_datetime(node.created),
            'dateModified': _to_datetime(node.modified),
            'creator': {
                '@id': user_ids[node.creator._id],
            },
            'contributor': [
                {
                    '@id': user_ids[user._id],
                }
                for user in node.contributors.all()
            ],
            'keywords': [t.name for t in node.tags.all()],
        }
        if extra_props:
            props.update(extra_props)
        if not node.license:
            return [
                ContextEntity(crate, entity_id, properties=props),
            ]
        license_entity_id = node.license.license_id
        license = ContextEntity(crate, license_entity_id, properties={
            '@type': 'RDMLicense',
            'name': node.license.name,
            'description': node.license.text,
            'url': node.license.url,
            'rdmLicenseYear': node.license.year,
            'rdmLicenseCopyrightHolders': node.license.copyright_holders,
            'rdmLicenseProperties': list(node.license.node_license.properties),
        })
        props['license'] = {
            '@id': license_entity_id,
        }
        return [
            ContextEntity(crate, entity_id, properties=props),
            license,
        ]

    def _create_project_metadata_entities(self, crate, node, draft_or_registration, node_ids, schema_ids, project_metadata_ids):
        metadata_props, new_schema_ids = convert_project_metadata_to_json_ld_entities(draft_or_registration)
        project_metadata_id = f'#project-metadata#{len(project_metadata_ids)}'
        project_metadata_ids[draft_or_registration._id] = project_metadata_id
        metadata_props.update({
            'about': {
                '@id': node_ids[node._id],
            },
        })
        crate.add(ContextEntity(crate, project_metadata_id, properties=metadata_props))
        for schema_id, schema_props in new_schema_ids.items():
            if schema_id in schema_ids:
                continue
            schema_ids[schema_id] = schema_props
            crate.add(ContextEntity(crate, schema_id, properties=schema_props))

    def _create_file_metadata_entities(self, crate, node, path, file_path, schema_ids):
        metadata = node.get_addon(SHORT_NAME)
        if metadata is None:
            return
        file_metadata = metadata.get_file_metadata_for_path(file_path, resolve_parent=False)
        if file_metadata is None:
            return
        file_entity_id = path
        if not file_metadata['folder'] and file_entity_id.startswith('./'):
            file_entity_id = file_entity_id[2:]
        file_metadata_props, new_schema_ids = convert_file_metadata_to_json_ld_entities(file_metadata)
        for i, entity in enumerate(file_metadata_props):
            props = {
                'dateCreated': file_metadata['created'],
                'dateModified': file_metadata['modified'],
            }
            props.update(entity)
            props['about'] = {
                '@id': file_entity_id,
            }
            crate.add(ContextEntity(crate, f'{file_entity_id}#{i}', properties=props))
        for schema_id, schema_props in new_schema_ids.items():
            if schema_id in schema_ids:
                continue
            schema_ids[schema_id] = schema_props
            crate.add(ContextEntity(crate, schema_id, properties=schema_props))

    def _create_comment_entities(self, crate, about_id, reply_for_id, comment, user_ids, comment_ids):
        if self.include_users and comment.user._id not in user_ids:
            crate.add(*self._create_contributor_entities(crate, comment.user, user_ids))
        if comment._id in comment_ids:
            # already added
            return []
        comment_id = f'#comment#{len(comment_ids)}'
        comment_ids[comment._id] = comment_id
        props = {
            '@type': 'Comment',
            'dateCreated': _to_datetime(comment.created),
            'dateModified': _to_datetime(comment.modified),
            'text': comment.content,
            'author': {
                '@id': user_ids[comment.user._id]
            } if comment.user._id in user_ids else None
        }
        if reply_for_id is not None:
            props['parentItem'] = {
                '@id': reply_for_id,
            }
        if about_id is not None:
            props['about'] = {
                '@id': about_id,
            }
        r = [ContextEntity(crate, comment_id, properties=props)]
        for reply in Comment.objects.filter(target___id=comment._id, deleted__isnull=True):
            r += self._create_comment_entities(crate, None, comment_id, reply, user_ids, comment_ids)
        return r

    def _create_creator_entities(self, crate, user, user_ids):
        if user._id in user_ids:
            return []
        entity_id = f'#creator{len(user_ids)}'
        user_ids[user._id] = entity_id
        return self._create_person_entities(crate, user, entity_id, user_ids)

    def _create_contributor_entities(self, crate, user, user_ids):
        if user._id in user_ids:
            return []
        entity_id = f'#contributor{len(user_ids)}'
        user_ids[user._id] = entity_id
        return self._create_person_entities(crate, user, entity_id, user_ids)

    def _create_person_entities(self, crate, user, entity_id, user_ids):
        person_props = {
            'name': user.fullname,
            'givenName': _to_localized(user, 'given_name'),
            'familyName': _to_localized(user, 'family_name'),
            'identifier': _to_identifier(user),
        }
        current_jobs = [j for j in user.jobs if j['ongoing']]
        current_schools = [s for s in user.schools if s['ongoing']]
        affiliation = None
        if len(current_jobs) > 0:
            person_props['jobTitle'] = current_jobs[0]['title']
            affiliation = current_jobs[0]
        elif len(current_schools) > 0:
            person_props['jobTitle'] = current_schools[0]['degree']
            affiliation = current_schools[0]
        if affiliation is None:
            return [
                Person(crate, entity_id, properties=person_props),
            ]
        institution_id = f'#{affiliation["institution"] or affiliation["institution_ja"]}'
        if affiliation['department'] or affiliation['department_ja']:
            organization_id = f'{institution_id}#{affiliation["department"] or affiliation["department_ja"]}'
        else:
            organization_id = institution_id
        if organization_id in user_ids:
            return [
                Person(crate, entity_id, properties=person_props),
            ]
        user_ids[institution_id] = affiliation
        user_ids[organization_id] = affiliation
        person_props['affiliation'] = {
            '@id': organization_id,
        }
        institution_name = []
        if affiliation['institution']:
            institution_name.append({
                '@language': 'en',
                '@value': affiliation['institution'],
            })
        if affiliation['institution_ja']:
            institution_name.append({
                '@language': 'ja',
                '@value': affiliation['institution_ja'],
            })
        institution_props = {
            '@type': 'Organization',
            'name': institution_name,
        }
        if not (affiliation['department'] or affiliation['department_ja']):
            return [
                Person(crate, entity_id, properties=person_props),
                ContextEntity(crate, institution_id, properties=institution_props),
            ]
        department_name = []
        if affiliation['department']:
            department_name.append({
                '@language': 'en',
                '@value': affiliation['department'],
            })
        if affiliation['department_ja']:
            department_name.append({
                '@language': 'ja',
                '@value': affiliation['department_ja'],
            })
        department = ContextEntity(crate, organization_id, properties={
            '@type': 'Organization',
            'name': department_name,
        })
        institution_props['department'] = {
            '@id': organization_id,
        }
        return [
            Person(crate, entity_id, properties=person_props),
            department,
            ContextEntity(crate, institution_id, properties=institution_props),
        ]

    def _create_log_entity(self, crate, log, user_ids, action_ids):
        if log._id in action_ids:
            # already added
            return None
        action_id = f'#action#{len(action_ids)}'
        action_ids[log._id] = action_id
        return ContextEntity(crate, action_id, properties={
            '@type': 'Action',
            'name': log.action,
            'startTime': _to_datetime(log.date),
            'agent': {
                '@id': user_ids[log.user._id]
            } if log.user is not None and log.user._id in user_ids else None,
        })

    def _create_addon_entity(self, crate, node_id, addon, extra_props=None):
        props = {
            '@type': 'RDMAddon',
            'name': addon.config.short_name,
            'description': addon.config.full_name,
            'about': {
                '@id': node_id,
            },
        }
        if hasattr(addon, 'folder_id'):
            props['rdmFolderId'] = addon.folder_id
        if extra_props is not None:
            props.update(extra_props)
        return ContextEntity(crate, f'{node_id}-{addon.config.short_name}', properties=props)

    def _create_wiki_entities(self, crate, base_path, wiki, user_ids, comment_ids):
        r = []
        path = os.path.join(base_path, wiki.page_name)
        comments = []
        creator = None
        latest = wiki.get_version()
        if latest is not None:
            creator = latest.user
        if self.include_users and creator._id not in user_ids:
            crate.add(*self._create_contributor_entities(crate, creator, user_ids))
        comments = sum([
            self._create_comment_entities(crate, path, None, c, user_ids, comment_ids)
            for c in Comment.objects.filter(root_target=Guid.load(wiki._id), deleted__isnull=True)
        ], [])
        first = wiki.versions.order_by('created').first()
        created = first.created if first is not None else None
        modified = latest.created if latest is not None else None
        r.append((path, WikiFile(wiki), comments))
        props = {
            'name': wiki.page_name,
            'encodingFormat': 'text/markdown',
            'contentSize': str(len(latest.content)) if latest is not None else None,
            'dateModified': modified.isoformat() if modified else None,
            'dateCreated': created.isoformat() if created else None,
        }
        if latest is not None:
            props['version'] = latest.identifier
        if creator is not None and creator._id in user_ids:
            props['creator'] = {
                '@id': user_ids[creator._id],
            }
        crate.add_file(path, dest_path=path, properties=props)
        return r

class WikiFile(object):
    def __init__(self, wiki):
        self.wiki = wiki

    @property
    def size(self):
        data = self._get_content_as_bytes()
        return len(data) if data is not None else 0

    def download_to(self, f):
        data = self._get_content_as_bytes()
        if data is None:
            logger.warn(f'Wiki content is empty: {self.wiki.page_name}')
            return
        f.write(data)

    def _get_content_as_bytes(self):
        latest = self.wiki.get_version()
        if latest is None:
            return None
        return latest.content.encode('utf8')

class ROCrateFactory(BaseROCrateFactory):

    def __init__(self, node, work_dir, wb, config):
        super(ROCrateFactory, self).__init__(node, work_dir)
        self.wb = wb
        self.config = config

    def _create_comment_entities(self, crate, parent_id, reply_for_id, comment, user_ids, comment_ids):
        comment_config = self.config.get('comment', {})
        if not comment_config.get('enable', True):
            return []
        return super()._create_comment_entities(crate, parent_id, reply_for_id, comment, user_ids, comment_ids)

    def _is_file_archivable(self, wb_file):
        provider = wb_file.attributes['provider']
        addons_config = self.config.get('addons', {})
        materialized = wb_file.attributes['materialized']
        logger.debug(f'is_file_archivable: {materialized}, provider={provider}, files={addons_config}')
        if provider not in addons_config:
            return False
        files = addons_config[provider].get('files', [])
        if len(files) == 0:
            files = DEFAULT_ADDONS_FILES
        files = [
            f
            for f in files
            if f['materialized'] == materialized
        ]
        if len(files) == 0:
            return True
        return files[0].get('enable', False)

    def _create_project_related_entities(
        self, crate, base_file_prefix, node,
        user_ids, node_ids, schema_ids, comment_ids, action_ids, project_metadata_ids,
        extra_props=None,
    ):
        entity_id = node_ids[node._id]
        file_prefix = f'{base_file_prefix}{entity_id[1:]}/'
        # child nodes
        child_entities = []
        child_files = []
        for child in node.nodes:
            if child._id in node_ids:
                continue
            node_ids[child._id] = f'#node{len(node_ids)}'
            child_entities_, child_files_ = self._create_project_related_entities(
                crate, base_file_prefix, child,
                user_ids, node_ids, schema_ids, comment_ids, action_ids, project_metadata_ids,
            )
            child_entities += child_entities_
            child_files += child_files_
        # project for this node
        node_extra_props = {
            'hasPart': [
                {
                    '@id': node_ids[child._id],
                }
                for child in node.nodes
            ],
        }
        if extra_props:
            node_extra_props.update(extra_props)
        entities = []
        entities += self._create_project_entities(
            crate,
            entity_id,
            node,
            user_ids,
            extra_props=node_extra_props,
        )
        entities += sum([
            self._create_comment_entities(crate, entity_id, None, comment, user_ids, comment_ids)
            for comment in Comment.objects.filter(root_target=Guid.load(node._id), deleted__isnull=True)
        ], [])
        files = []
        # addons
        wb = self.wb.get_client_for_node(node)
        addons_config = self.config.get('addons', {})
        for addon_app in website_settings.ADDONS_AVAILABLE:
            addon_name = addon_app.short_name
            if addon_name == 'wiki':
                # wiki is handled separately
                continue
            addon = node.get_addon(addon_name)
            if addon is None:
                continue
            if addon_name in addons_config and not addons_config[addon_name].get('enable', True):
                logger.info(f'Skipped {addon_name}')
                crate.add(self._create_addon_entity(
                    crate,
                    entity_id,
                    addon,
                ))
                continue
            if not (hasattr(addon, 'serialize_waterbutler_credentials') and addon.complete):
                crate.add(self._create_addon_entity(
                    crate,
                    entity_id,
                    addon,
                ))
                continue
            provider_files = []
            for file in wb.get_root_files(addon_name):
                entity, children = self._create_file_entities(crate, node, f'{file_prefix}{addon_name}', file, user_ids, schema_ids, comment_ids)
                if entity is None:
                    # skip unarchivable file
                    continue
                files += children
                provider_files.append(entity)
            crate.add(self._create_addon_entity(
                crate,
                entity_id,
                addon,
                extra_props={
                    'hasPart': [
                        {
                            '@id': entity.id,
                        }
                        for entity in provider_files
                    ],
                },
            ))
        # project metadata
        drafts = DraftRegistration.objects.filter(branched_from=node)
        for draft in drafts.all():
            self._create_project_metadata_entities(crate, node, draft, node_ids, schema_ids, project_metadata_ids)
        registrations = Registration.objects.filter(registered_from=node)
        for registration in registrations.all():
            self._create_project_metadata_entities(crate, node, registration, node_ids, schema_ids, project_metadata_ids)
        # related entities
        wiki_config = self.config.get('wiki', {})
        if wiki_config.get('enable', True):
            wikis = []
            for wiki in node.wikis.filter(deleted__isnull=True):
                wikis += self._create_wiki_entities(crate, f'{file_prefix}wiki/', wiki, user_ids, comment_ids)
            crate.add(self._create_addon_entity(
                crate,
                entity_id,
                node.get_addon('wiki'),
                extra_props={
                    'hasPart': [
                        {
                            '@id': path[2:] if path.startswith('./') else path,
                        }
                        for path, _, _ in wikis
                    ],
                },
            ))
            files += wikis
        log_config = self.config.get('log', {})
        if log_config.get('enable', True):
            for log in node.logs.all():
                entity = self._create_log_entity(crate, log, user_ids, action_ids)
                if entity is None:
                    continue
                entities.append(entity)
        for _, _, comments in files:
            entities += comments
        return entities + child_entities, files + child_files

    def _build_ro_crate(self, crate):
        user_ids = {}
        files = []
        creators = []
        contributors = []
        for node in [self.node] + list(self.node.get_descendants_recursive()):
            creators += self._create_creator_entities(crate, node.creator, user_ids)
            contributors += sum(
                [self._create_contributor_entities(crate, user, user_ids) for user in node.contributors.all()],
                [],
            )
        node_ids = {
            self.node._id: '#root',
        }
        schema_ids = {}
        comment_ids = {}
        action_ids = {}
        project_metadata_ids = {}
        project_entities, project_files = self._create_project_related_entities(
            crate,
            './',
            self.node,
            user_ids,
            node_ids,
            schema_ids,
            comment_ids,
            action_ids,
            project_metadata_ids,
            extra_props={
                'about': {
                    '@id': './',
                },
            },
        )
        crate.add(*project_entities)
        files += project_files
        crate.add(*creators)
        crate.add(*contributors)
        return crate, files

class ROCrateExtractor(object):

    def __init__(self, user, url, work_dir):
        self.user = user
        self.url = url
        self.work_dir = work_dir
        self.zip_path = None
        self._crate = None
        self.related_nodes = {}

    def ensure_node(self, node, node_id='#root'):
        self.related_nodes[node_id] = node
        entity = self.crate.get(node_id)
        node.description = self._extract_description(node_id)
        if 'category' in entity.properties():
            node.category = entity.properties()['category']

        # tags
        for keyword in self.crate.get(node_id).properties().get('keywords', []):
            self._ensure_tag(node, keyword)

        # restore addons
        for addon in self._find_related_entities(node_id, lambda e: e.type == 'RDMAddon'):
            self._ensure_addon(node, addon)

        # child nodes
        children = entity.properties().get('hasPart', [])
        for child_ref in children:
            child_id = child_ref['@id']
            child_node = self._create_child_node(node, self.crate.get(child_id))
            self.ensure_node(child_node, node_id=child_id)

        node.save()

    def _create_child_node(self, node, child):
        title = self._extract_title(child.id)
        auth = Auth(user=node.creator)
        serializer = NodeSerializer(context={
            'request': RequestWrapper(auth),
        })
        return serializer.create({
            'title': title,
            'category': 'project',
            'creator': auth.user,
            'parent': node,
        })

    def _ensure_addon(self, node, addon):
        addon_name = addon.properties()['name']
        addon_object = node.get_addon(addon_name)
        if addon_object is None:
            addon_object = node.add_addon(addon_name, auth=Auth(user=self.user), log=False)
        folder_id = addon.properties().get('rdmFolderId', None)
        if not folder_id:
            return
        metadata_addon = node.get_or_add_addon(METADATA_SHORT_NAME, auth=Auth(user=self.user))
        metadata_addon.add_imported_addon_settings(addon_name, folder_id)

    def ensure_folders(self, wb):
        addons = [
            e
            for e in self.crate.get_entities()
            if e.type == 'RDMAddon'
        ]
        for addon_entity in addons:
            node = self.related_nodes[addon_entity.properties()['about']['@id']]
            addon_name = addon_entity.properties()['name']
            for part in addon_entity.properties().get('hasPart', []):
                file = self._crate.get(part['@id'])
                if file.type != 'RDMFolder':
                    continue
                self._ensure_folders(
                    wb,
                    node,
                    f'{addon_name}/',
                    file,
                )

    def _ensure_folders(self, wb, node, base_path, folder):
        path = os.path.join(base_path, folder.properties()['name']) + '/'
        logger.info(f'Ensuring folders: {path}')
        wb.get_client_for_node(node).get_file_by_materialized_path(path, create=True)
        self._ensure_file_metadata(node, folder, path)
        for part in folder.properties().get('hasPart', []):
            file = self._crate.get(part['@id'])
            if file.type != 'RDMFolder':
                continue
            self._ensure_folders(
                wb,
                node,
                path,
                file,
            )

    def _find_related_entities(self, about_id, filter):
        return [
            e
            for e in self.crate.get_entities()
            if e.properties().get('about', {}).get('@id', None) == about_id and
            filter(e)
        ]

    def _extract_description(self, node_id):
        crate = self.crate
        value = _extract_ro_crate_value(
            crate,
            crate.get(node_id),
            'description',
        )
        return _extract_value(value)

    def _extract_title(self, node_id):
        crate = self.crate
        value = _extract_ro_crate_value(
            crate,
            crate.get(node_id),
            'name',
        )
        return _extract_value(value)

    @property
    def crate(self):
        if self._crate is not None:
            return self._crate
        self._crate = self._load_ro_crate()
        return self._crate

    @property
    def file_extractors(self):
        with ZipFile(self.zip_path, 'r') as zf:
            for i, file_name in enumerate(zf.namelist()):
                file = self.crate.get(file_name)
                if file.type == 'CreativeWork':
                    # ro-crate-metadata.json does not need to be restored
                    continue
                logger.info(f'Restoring... {file_name}')
                archive_path = os.path.join(*[e.properties()['name'] for e in self._get_path_for_file(file_name)])
                addon = self._find_addon_for_file(file_name)
                if addon.config.short_name == 'wiki':
                    data_buf = io.BytesIO()
                    with zf.open(file_name, 'r') as sf:
                        shutil.copyfileobj(sf, data_buf)
                    data_buf.seek(0)
                    yield WikiExtractor(
                        self,
                        file,
                        addon,
                        archive_path,
                        data_buf,
                    )
                    continue
                data_path = os.path.join(self.work_dir, f'data{i}.dat')
                with zf.open(file_name, 'r') as sf:
                    with open(data_path, 'wb') as df:
                        shutil.copyfileobj(sf, df)
                yield FileExtractor(
                    self,
                    file,
                    addon,
                    archive_path,
                    data_path,
                )

    def _find_parent_entities_for_file(self, file_path):
        return [
            e
            for e in self.crate.get_entities()
            if file_path in [part.get('@id', None) for part in e.properties().get('hasPart', [])]
        ]

    def _find_addon_for_file(self, file_path):
        parents = self._find_parent_entities_for_file(file_path)
        if len(parents) == 0:
            raise ValueError(f'No parent entities for {file_path}')
        parents = [e for e in parents if e.type.startswith('RDM')]
        if len(parents) == 0:
            raise ValueError(f'No parent RDM entities for {file_path}')
        parent = parents[0]
        if parent.type == 'RDMFolder':
            return self._find_addon_for_file(parent.id)
        if parent.type != 'RDMAddon':
            raise ValueError(f'Unexpected parent type: {parent.type}')
        node_id = parent.properties()['about']['@id']
        node = self.related_nodes[node_id]
        return node.get_addon(parent.properties()['name'])

    def _get_path_for_file(self, file_path):
        file = self.crate.get(file_path)
        return self._get_parent_path_for_file(file_path) + [file]

    def _get_parent_path_for_file(self, file_path):
        parents = self._find_parent_entities_for_file(file_path)
        if len(parents) == 0:
            raise ValueError(f'No parent entities for {file_path}')
        parents = [e for e in parents if e.type.startswith('RDM')]
        if len(parents) == 0:
            raise ValueError(f'No parent RDM entities for {file_path}')
        parent = parents[0]
        if parent.type == 'RDMAddon':
            return [parent]
        if parent.type != 'RDMFolder':
            raise ValueError(f'Unexpected parent type: {parent.type}')
        return self._get_parent_path_for_file(parent.id) + [parent]

    def _load_ro_crate(self):
        self.zip_path = os.path.join(self.work_dir, 'package.zip')
        with open(self.zip_path, 'wb') as f:
            self._download(f)
        logger.debug(f'Downloaded: {os.path.getsize(self.zip_path)}')

        file_name = 'ro-crate-metadata.json'
        with ZipFile(self.zip_path, 'r') as zf:
            with zf.open(file_name, 'r') as sf:
                logger.debug(f'ZIP-CONTENT: {file_name}')
                json_path = os.path.join(self.work_dir, file_name)
                with open(json_path, 'wb') as df:
                    shutil.copyfileobj(sf, df)
                return ROCrate(self.work_dir)

    def _download(self, file):
        resp = requests.get(self.url, stream=True)
        logger.info(f'GET {self.url} => {resp.status_code}, {resp.url}')
        # Check whether the response is login page
        resp_is_html = resp.headers['content-type'].startswith('text/html')
        if resp.status_code == 200 and 'login' in resp.url and resp_is_html:
            raise PermissionsError(f'URL {self.url} is not publicly accessible')
        resp.raise_for_status()
        resp.raw.decode_content = True
        shutil.copyfileobj(resp.raw, file)

    def _ensure_tag(self, node, keyword):
        if keyword in [t.name for t in node.tags.all()]:
            return
        node.add_tags([keyword], auth=Auth(user=self.user), log=False)

    def _ensure_file_metadata(self, node, entity, file_path):
        metadata_entities = [
            e
            for e in self.crate.get_entities()
            if e.properties().get('about', {}).get('@id', None) == entity.id and
            e.type == 'RDMFileMetadata'
        ]
        if len(metadata_entities) == 0:
            return
        logger.debug(f'Metadata for {entity.id}({file_path}) = {metadata_entities}')
        metadata_addon = node.get_addon(SHORT_NAME)
        if metadata_addon is None:
            return
        items = [
            convert_json_ld_entity_to_file_metadata_item(e.properties(), self._crate)
            for e in metadata_entities
        ]
        metadata_addon.set_file_metadata(file_path, {
            'path': file_path,
            'folder': file_path.endswith('/'),
            'hash': '',
            'items': [i for i in items if i is not None],
        })

class BaseExtractor(object):
    def __init__(self, owner, entity, addon):
        self.owner = owner
        self.entity = entity
        self.addon = addon

    @property
    def node(self):
        return self.addon.owner

    def extract(self, wb):
        raise NotImplementedError()


class FileExtractor(BaseExtractor):
    def __init__(self, owner, entity, addon, file_path, data_path):
        super(FileExtractor, self).__init__(owner, entity, addon)
        self.file_path = file_path
        self.data_path = data_path

    def extract(self, wb_client):
        wb = wb_client.get_client_for_node(self.node)
        folder_name, file_name_ = os.path.split(self.file_path)
        file = wb.get_file_by_materialized_path(folder_name + '/')
        if file is None:
            raise IOError(f'No such directory: {folder_name}/')
        new_file = file.upload_file(self.data_path, file_name_)
        os.remove(self.data_path)
        file_node = _as_web_file(self.node, new_file)
        self._ensure_metadata(file_node)
        self.owner._ensure_file_metadata(self.node, self.entity, self.file_path)

    def _ensure_metadata(self, file_node):
        for keyword in self.entity.properties().get('keywords', []):
            self.owner._ensure_tag(file_node, keyword)
        file_node.save()


class WikiExtractor(BaseExtractor):
    def __init__(self, owner, entity, addon, file_path, data_buf):
        super(WikiExtractor, self).__init__(owner, entity, addon)
        self.file_path = file_path
        self.data_buf = data_buf

    def extract(self, wb):
        wiki_name = self.entity.properties()['name']
        WikiPage.objects.create_for_node(
            self.node,
            wiki_name,
            self.data_buf.getvalue().decode('utf8'),
            Auth(user=self.owner.user),
        )


def _to_datetime(d):
    return d.isoformat()

def fill_license_params(license_text, node_license):
    params = node_license.to_json()
    for k, v in params.items():
        pk = _snake_to_camel(k)
        if isinstance(v, list):
            if len(v) == 0:
                continue
            v = v[0]
        license_text = re.sub(r'{{\s*' + pk + r'\s*}}', v, license_text)
    return license_text

def to_creators_metadata(users):
    return [
        _to_user_metadata(user)
        for user in users
    ]

def _to_user_metadata(user):
    return {
        'number': user.erad,
        'name-ja': {
            'last': user.family_name_ja,
            'middle': user.middle_names_ja,
            'first': user.given_name_ja,
        },
        'name-en': {
            'last': user.family_name,
            'middle': user.middle_names,
            'first': user.given_name,
        },
    }

def _snake_to_camel(name):
    components = name.split('_')
    return components[0] + ''.join([c.capitalize() for c in components[1:]])

def _to_localized(o, prop, default_lang='en'):
    items = []
    items.append(dict([('@value', getattr(o, prop))] + ([('@language', default_lang)] if default_lang else [])))
    prop_ja = f'{prop}_ja'
    if not hasattr(o, prop_ja):
        return items
    value_ja = getattr(o, prop_ja)
    if not value_ja:
        return items
    items.append({
        '@value': value_ja,
        '@language': 'ja',
    })
    return items

def _to_i18n_property_key(name, language):
    if language == 'en':
        return name
    return f'{name}_{language}'

def _to_i18n_metadata(prefix, object, names, languages=['ja', 'en'], get_value=getattr):
    r = {}
    for language in languages:
        keys = [_to_i18n_property_key(name, language) for name in names]
        values = [get_value(object, key, '') for key in keys]
        r[f'{prefix}{language}'] = to_metadata_value(' '.join(values))
    return r

def to_metadata_value(value):
    return {
        'extra': [],
        'comments': [],
        'value': value,
    }

def _extract_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        assert '@value' in value, value
        return value['@value']
    assert isinstance(value, list), value
    return _extract_value(value[0])

def _extract_ro_crate_value(crate, entity, param):
    return entity.properties()[param]

def _to_identifier(user):
    values = []
    if user.erad:
        values.append({
            '@type': 'PropertyValue',
            'propertyID': 'e-Rad_Researcher',
            'value': user.erad,
        })
    social = user.social
    for k, v in user.SOCIAL_FIELDS.items():
        if k not in social:
            continue
        value = social[k]
        if not value:
            continue
        if v:
            if isinstance(value, list):
                value = [v.format(v_) for v_ in value]
            else:
                value = v.format(value)
        values.append({
            '@type': 'PropertyValue',
            'propertyID': k,
            'value': value,
        })
    return values

@celery_app.task(bind=True, max_retries=3)
def export_project(self, user_id, node_id, config):
    user = OSFUser.load(user_id)
    node = AbstractNode.load(node_id)
    wb = WaterButlerClient(user)
    metadata_addon = node.get_addon(SHORT_NAME)
    schema_id = RegistrationSchema.objects \
        .filter(name=EXPORT_REGISTRATION_SCHEMA_NAME) \
        .order_by('-schema_version') \
        .first()._id
    as_ro_crate_json = config.get('json_only', False)
    logger.info(f'Exporting: {node_id}')
    self.update_state(state='exporting node', meta={
        'progress': 0,
        'user': user_id,
        'node': node_id,
    })
    work_dir = tempfile.mkdtemp()
    try:
        rocrate = ROCrateFactory(node, work_dir, wb, config)
        zip_path = os.path.join(work_dir, 'package.zip')
        if as_ro_crate_json:
            return {
                'user': user_id,
                'node': node_id,
                'json': rocrate.get_ro_crate_json(),
            }
        rocrate.download_to(zip_path)
        now = datetime.now().strftime('%Y%m%d-%H%M%S')
        file_name_ = f'.rdm-project-{now}.zip'
        provider_name = config['destination']['provider']
        uploaded = wb.get_client_for_node(node).upload_root_file(zip_path, file_name_, provider_name)
        default_data = {
            'grdm-file:title-ja': to_metadata_value(node.title),
            'grdm-file:data-description-ja': to_metadata_value(node.description),
            'grdm-file:creators': to_metadata_value(to_creators_metadata([user] if user is not None else [])),
            'grdm-file:data-type': to_metadata_value('dataset'),
            'grdm-file:data-man-type': to_metadata_value('organization'),
        }
        if node.node_license is not None:
            default_data['grdm-file:data-policy-license'] = to_metadata_value(node.node_license.license_id)
        current_jobs = [job for job in user.jobs if job['ongoing']]
        if len(current_jobs) > 0:
            default_data.update(_to_i18n_metadata(
                'grdm-file:data-man-org-',
                current_jobs[0],
                ['institution', 'department'],
                get_value=lambda o, k, default: html.unescape(o[k]) if k in o else default,
            ))
        institutions = node.affiliated_institutions.all()
        if len(institutions) > 0:
            default_data['grdm-file:hosting-inst-ja'] = to_metadata_value(institutions[0].name)
        metadata = {
            'path': f'{provider_name}/{file_name_}',
            'folder': False,
            'hash': '',
            'items': [
                {
                    'active': True,
                    'schema': schema_id,
                    'data': default_data,
                }
            ],
        }
        metadata_addon.set_file_metadata(metadata['path'], metadata)
        self.update_state(state='finished', meta={
            'progress': 100,
            'user': user_id,
            'node': node_id,
            'file': {
                'data': uploaded.attributes,
            },
        })
        return {
            'user': user_id,
            'node': node_id,
            'file': {
                'data': uploaded.attributes,
            },
        }
    finally:
        shutil.rmtree(work_dir)

def _create_node(user, node_title):
    auth = Auth(user)
    serializer = NodeSerializer(context={
        'request': RequestWrapper(auth),
    })
    return serializer.create({
        'title': node_title,
        'category': 'project',
        'creator': auth.user,
    })

@celery_app.task(bind=True, max_retries=3)
def import_project(self, url, user_id, node_title):
    user = OSFUser.load(user_id)
    wb = WaterButlerClient(user)
    work_dir = tempfile.mkdtemp()
    logger.info(f'Importing: {url} -> (new node), {work_dir}')
    self.update_state(state='provisioning node', meta={
        'progress': 0,
        'user': user_id,
    })
    try:
        extractor = ROCrateExtractor(user, url, work_dir)
        logger.info(f'RO-Crate loaded: {extractor.crate}')
        node = _create_node(user, node_title)
        node_id = node._id
        extractor.ensure_node(node)
        self.update_state(state='provisioning folders', meta={
            'progress': 10,
            'user': user_id,
            'node': node_id,
        })
        extractor.ensure_folders(wb)
        self.update_state(state='provisioning files', meta={
            'progress': 50,
            'user': user_id,
            'node': node_id,
        })
        for file_extractor in extractor.file_extractors:
            file_extractor.extract(wb)
        self.update_state(state='finished', meta={
            'progress': 100,
            'user': user_id,
            'node': node_id,
        })
        return {
            'user': user_id,
            'node': node_id,
            'crate': {
                'title': node.title,
                'description': node.description,
            },
        }
    finally:
        shutil.rmtree(work_dir)

def get_task_result(auth, task_id):
    result = celery_app.AsyncResult(task_id)
    error = None
    info = {}
    if result.failed():
        logger.info(f'Failed: {result.info}: {type(result.info)}')
        error = str(result.info)
    elif result.info is not None and auth.user._id != result.info['user']:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    elif result.info is not None:
        info.update(result.info)
        if 'node' in result.info:
            node = AbstractNode.load(result.info['node'])
            info['node_url'] = node.web_url_for('view_project')
            if 'file' in result.info:
                file = result.info['file']['data']
                path = file['path'].lstrip('/')
                provider = file['provider']
                file_url = node.web_url_for('addon_view_or_download_file',
                                            path=path, provider=provider)
                info['file_url'] = file_url
            elif 'json' in result.info:
                info['json'] = result.info['json']
    return {
        'state': result.state,
        'info': info,
        'error': error,
    }
