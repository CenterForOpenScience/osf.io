import gc
from datetime import datetime

import pytz
from django.db import transaction
from framework.auth import User as MODMUser
from modularodm import Q as MQ
from osf_models.models import Contributor, Guid, Node, Tag, User
from website.models import Node as MODMNode
from website.models import Tag as MODMTag


class DryMigrationException(BaseException):
    pass


fk_node_fields = [
    'forked_from', 'registered_from', 'root', 'parent_node', 'template_node',
    '_primary_institution'
]
m2m_node_fields = ['nodes', '_affiliated_institutions']
fk_user_fields = ['registered_user', 'creator', 'merged_by']
m2m_user_fields = [
    'permissions', 'recently_added', 'users_watching_node', 'contributors',
    '_affiliated_institutions'
]
m2m_tag_fields = ['tags', 'system_tags']

node_key_blacklist = [
    '__backrefs',
    '_version',
    'expanded',
    # foreign keys not yet implemented
    'logs',
    'primary_institution',
    #  '_primary_institution',
    #  'institution_email_domains',
    #  'institution_domains',
    'registration_approval',
    'alternative_citations',
    'registered_schema',
    'affiliated_institutions',
    #  '_affiliated_institutions',
    #  'institution_banner_name',
    #  'institution_id',
    #  'institution_auth_url',
    #  'institution_logo_name',
    'contributors',  # done elsewhere
    'retraction',
    'embargo',
    'node_license',
] + fk_user_fields + fk_node_fields + m2m_node_fields + m2m_user_fields + m2m_tag_fields
user_key_blacklist = [
    '__backrefs',
    '_version',
    'affiliated_institutions',
    # '_affiliated_institutions',
    'watched',
    'external_accounts',
] + fk_user_fields + fk_node_fields + m2m_node_fields + m2m_user_fields + m2m_tag_fields

tag_key_blacklist = ['_version',
                     '__backrefs',
                     ] + m2m_node_fields + m2m_user_fields + m2m_tag_fields


def save_bare_nodes(page_size=20000):
    print 'Starting save_bare_nodes...'
    count = 0
    start = datetime.now()
    total = MODMNode.find(allow_institution=True).count()
    while count < total:
        with transaction.atomic():
            nids = []
            for modm_node in MODMNode.find(
                    allow_institution=True).sort('-date_modified')[
                        count:count + page_size]:
                guid = Guid.objects.get(guid=modm_node._id)
                node_fields = dict(_guid_id=guid.pk, **modm_node.to_storage())

                # remove fields not yet implemented
                cleaned_node_fields = {key: node_fields[key]
                                       for key in node_fields
                                       if key not in node_key_blacklist}

                # make datetimes not naive
                for k, v in cleaned_node_fields.iteritems():
                    if isinstance(v, datetime):
                        cleaned_node_fields[k] = pytz.utc.localize(v)

                # remove null fields, postgres hate null fields
                cleaned_node_fields = {k: v
                                       for k, v in
                                       cleaned_node_fields.iteritems()
                                       if v is not None}
                nids.append(Node(**cleaned_node_fields))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print 'Saving nodes {} through {}...'.format(
                        count - page_size, count)
                    woot = Node.objects.bulk_create(nids)
                    now = datetime.now()
                    print 'Done with {} nodes in {} seconds...'.format(
                        len(woot), (now - then).total_seconds())
                    nids = []
                    trash = gc.collect()
                    print 'Took out {} trashes'.format(trash)

    end = datetime.now()
    print 'Modm Nodes: {}'.format(total)
    print 'django Nodes: {}'.format(Node.objects.all().count())
    print 'Done with save_bare_nodes in {} seconds...'.format((
        end - start).total_seconds())


def save_bare_users(page_size=20000):
    print 'Starting save_bare_users...'
    count = 0
    start = datetime.now()
    total = MODMUser.find().count()

    while count < total:
        with transaction.atomic():
            users = []
            for modm_user in MODMUser.find().sort('-date_registered')[
                    count:count + page_size]:
                guid = Guid.objects.get(guid=modm_user._id)
                user_fields = dict(_guid_id=guid.pk, **modm_user.to_storage())

                cleaned_user_fields = {key: user_fields[key]
                                       for key in user_fields
                                       if key not in user_key_blacklist}

                for k, v in cleaned_user_fields.iteritems():
                    if isinstance(v, datetime):
                        cleaned_user_fields[k] = pytz.utc.localize(v)

                cleaned_user_fields = {k: v
                                       for k, v in
                                       cleaned_user_fields.iteritems()
                                       if v is not None}
                users.append(User(**cleaned_user_fields))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print 'Saving users {} through {}...'.format(
                        count - page_size, count)
                    woot = User.objects.bulk_create(users)
                    now = datetime.now()
                    print 'Done with {} users in {} seconds...'.format(
                        len(woot), (now - then).total_seconds())
                    users = None
                    woot = None
                    guid = None
                    user_fields = None
                    cleaned_user_fields = None
                    trash = gc.collect()
                    print 'Took out {} trashes'.format(trash)
    end = datetime.now()
    print 'Modm Users: {}'.format(total)
    print 'django Users: {}'.format(User.objects.all().count())
    print 'Done with save_bare_users in {} seconds...'.format((
        end - start).total_seconds())


def save_bare_tags(page_size=5000):
    print 'Starting save_bare_tags...'
    count = 0
    start = datetime.now()
    total = MODMTag.find().count()

    while count < total:
        with transaction.atomic():
            tags = []
            for modm_tag in MODMTag.find().sort('-_id')[count:count +
                                                        page_size]:
                tags.append(Tag(_id=modm_tag._id,
                                lower=modm_tag.lower,
                                system=False))
                count += 1
                if count % page_size == 0 or count == total:
                    then = datetime.now()
                    print 'Saving tags {} through {}...'.format(
                        count - page_size, count)
                    woot = Tag.objects.bulk_create(tags)
                    now = datetime.now()
                    print 'Done with {} tags in {} seconds...'.format(
                        len(woot), (now - then).total_seconds())
                    tags = None
                    woot = None
                    trash = gc.collect()
                    print 'Took out {} trashes'.format(trash)
    end = datetime.now()
    print 'MODM Tags: {}'.format(total)
    print 'django Tags: {}'.format(Tag.objects.all().count())
    print 'Done with save_bare_tags in {} seconds...'.format((
        end - start).total_seconds())


def save_bare_system_tags(page_size=10000):
    print 'Starting save_bare_system_tags...'
    start = datetime.now()

    things = list(MODMNode.find(MQ('system_tags', 'ne', [])).sort(
        '-_id')) + list(MODMUser.find(MQ('system_tags', 'ne', [])).sort(
            '-_id'))

    system_tag_ids = []
    for thing in things:
        for system_tag in thing.system_tags:
            system_tag_ids.append(system_tag)

    unique_system_tag_ids = set(system_tag_ids)

    total = len(unique_system_tag_ids)

    system_tags = []
    for system_tag_id in unique_system_tag_ids:
        system_tags.append(Tag(_id=system_tag_id, lower=system_tag_id.lower(), system=True))

    woot = Tag.objects.bulk_create(system_tags)

    print 'MODM System Tags: {}'.format(total)
    print 'django system tags: {}'.format(Tag.objects.filter(system=True).count())


def main(dry=True):
    modm_node_cache = {
        # 'modm_guid': 'django_pk'
    }
    django_node_cache = {
        # 'django_pk': 'modm_guid'
    }

    save_bare_nodes()
    save_bare_users()
    save_bare_tags()
    save_bare_system_tags()
    # set_foreign_keys()

    # if dry:
    #     raise DryMigrationException()
