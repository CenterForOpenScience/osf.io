from website.app import init_app

init_app()

# MIGRATE NODES

from website.models import Node as MODMNode
from website.models import Tag as MODMTag
from website.models import Pointer as MODMPointer
from modularodm import Q
from osf_models.models import Node, User, Tag, Guid, Contributor
import pytz
from datetime import datetime
import gc


fk_node_fields = [
    'forked_from',
    'registered_from',
    'root',
    'parent_node',
    'template_node',
    '_primary_institution'
]
m2m_node_fields = [
    'nodes',
    '_affiliated_institutions'
]
fk_user_fields = [
    'registered_user',
    'creator',
    'merged_by'
]
m2m_user_fields = [
    'permissions',
    'recently_added',
    'users_watching_node',
    'contributors',
    '_affiliated_institutions'
]
m2m_tag_fields = [
    'tags',
    'system_tags'
]

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
                        'contributors', # done elsewhere
                         'retraction',
                         'embargo',
                         'node_license',
                     ] + m2m_node_fields + m2m_user_fields + m2m_tag_fields
user_key_blacklist = [
                        '__backrefs',
                        '_version',
                        'affiliated_institutions',
                        # '_affiliated_institutions',
                        'watched',
                        'external_accounts',
                    ] + m2m_node_fields + m2m_user_fields + m2m_tag_fields

tag_key_blacklist = ['_version', '__backrefs', ] + m2m_node_fields + m2m_user_fields + m2m_tag_fields

nodes = 0
tags = 0
users = 0

all_of_the_things = {}
level = 0


def process_node_fk_fields(modm_object):
    fk_nodes = {}
    for fk_node_field in fk_node_fields:
        value = getattr(modm_object, fk_node_field, None)
        if value is not None:
            if fk_node_field in ['root', 'forked_from', ] and value != modm_object:
                node = get_or_create_node(value)
                if node is not None:
                    fk_nodes[fk_node_field] = node
            else:
                fk_nodes[fk_node_field] = None
    return fk_nodes


def process_node_m2m_fields(modm_object):
    m2m_nodes = {}
    for m2m_node_field in m2m_node_fields:
        value = getattr(modm_object, m2m_node_field, None)
        if value is not None:
            if isinstance(value, list):
                for nv in value:
                    if nv != modm_object:
                    # prevent recursion
                        node = get_or_create_node(nv)
                        if node is not None:
                            if m2m_node_field in m2m_nodes:
                                m2m_nodes[m2m_node_field].append(node)
                            else:
                                m2m_nodes[m2m_node_field] = [node, ]
    return m2m_nodes


def process_user_fk_fields(modm_object):
    fk_users = {}
    for fk_user_field in fk_user_fields:
        modm_user = getattr(modm_object, fk_user_field, None)
        if modm_user is not None and modm_user != modm_object:
            user = get_or_create_user(modm_user)
            if user is not None:
                fk_users[fk_user_field] = user
    return fk_users


def process_user_m2m_fields(modm_object):
    m2m_users = {}
    for m2m_user_field in m2m_user_fields:
        value = getattr(modm_object, m2m_user_field, None)
        if isinstance(value, list):
            for uv in value:
                if uv != modm_object:
                    # prevent recursion
                    user = get_or_create_user(uv)
                    if user is not None:
                        if m2m_user_field in m2m_users:
                            m2m_users[m2m_user_field].append(user)
                        else:
                            m2m_users[m2m_user_field] = [user, ]
    return m2m_users


def process_tag_m2m_fields(modm_object):
    m2m_tags = {}
    for m2m_tag_field in m2m_tag_fields:
        value = getattr(modm_object, m2m_tag_field, None)
        if isinstance(value, list):
            for tv in value:
                if m2m_tag_field == 'system_tags':
                    system = True
                else:
                    system = False
                tag = get_or_create_tag(tv, system)
                if tag is not None:
                    if m2m_tag_field in m2m_tags:
                        m2m_tags[m2m_tag_field].append(tag)
                    else:
                        m2m_tags[m2m_tag_field] = [tag, ]

    return m2m_tags


def set_m2m_fields(object, fields):
    for key, value in fields.iteritems():
        attr = getattr(object, key)
        attr.add(*value)
    object.save()


def get_or_create_user(modm_user):
    if modm_user is None:
        return None
    try:
        user = all_of_the_things[modm_user._id]
        print 'Got {} from cache'.format(user)
    except KeyError:
        try:
            user = User.objects.get(_guid__guid=modm_user._id)
        except User.DoesNotExist:
            user_fk_nodes = process_node_fk_fields(modm_user)
            user_m2m_nodes = process_node_m2m_fields(modm_user)
            user_fk_users = process_user_fk_fields(modm_user)
            # user_m2m_users = process_user_m2m_fields(modm_user)
            user_m2m_tags = process_tag_m2m_fields(modm_user)
            user_fields = {}
            user_fields['_guid'] = Guid.objects.get(guid=modm_user._id)
            user_fields.update(modm_user.to_storage())
            user_fields.update(user_fk_nodes)
            user_fields.update(user_fk_users)
            user_fields = {k: v for k, v in user_fields.iteritems() if v is not None}
            for k, v in user_fields.iteritems():
                if isinstance(v, datetime):
                    user_fields[k] = pytz.utc.localize(v)
            user = User.objects.create(**{key: user_fields[key] for key in user_fields if key not in user_key_blacklist})
            global users
            users += 1
            set_m2m_fields(user, user_m2m_nodes)
            # set_m2m_fields(user, user_m2m_users)
            set_m2m_fields(user, user_m2m_tags)

        all_of_the_things[modm_user._id] = user
    return user


def get_or_create_tag(modm_tag, system=False):
    if not modm_tag:
        return None
    if isinstance(modm_tag, unicode):
        try:
            tag = Tag.objects.get(_id=modm_tag, system=system)
        except Tag.DoesNotExist:
            tag = Tag.objects.create(lower=modm_tag.lower(), _id=modm_tag, system=system)
    else:
        if system is True:
            # this should never happen.
            print 'Encountered `unicode` tag that was not a system_tag {}'.format(modm_tag._id)
        try:
            tag = Tag.objects.get(_id=modm_tag._id, system=system)
        except Tag.DoesNotExist:
            tag_fields = modm_tag.to_storage()
            cleaned_tag = {key: tag_fields[key] for key in tag_fields if key not in tag_key_blacklist}
            cleaned_tag['system'] = system
            tag = Tag.objects.create(**cleaned_tag)
            global tags
            tags += 1
    return tag


def set_contributors(node, modm_node):
    for modm_contributor in modm_node.contributors:
        try:
            user = User.objects.get(_guid__guid=modm_contributor._id)
        except User.DoesNotExist:
            user = get_or_create_user(modm_contributor)
        visible = modm_contributor._id in modm_node.visible_contributor_ids
        admin = 'admin' in modm_node.permissions[modm_contributor._id]
        read = 'read' in modm_node.permissions[modm_contributor._id]
        write = 'write' in modm_node.permissions[modm_contributor._id]
        try:
            contributor = Contributor.objects.get_or_create(user=user, visible=visible, admin=admin, read=read, write=write,
                                                     node=node)
        except BaseException as ex:
            print 'Caught exception creating contributor for node {} and user {}: {}'.format(node._id,
                                                                                             modm_contributor._id, ex)


def get_or_create_node(modm_node):
    if modm_node is None:
        return None
    try:
        node = all_of_the_things[modm_node._id]
        print 'Got {} from cache'.format(node)
    except KeyError:
        try:
            # try and get the node
            node = Node.objects.get(_guid__guid=modm_node._id)
        except Node.DoesNotExist:
            # if it doesn't exist, check to see if the guid does
            try:
                guid = Guid.objects.get(guid=modm_node._id)
            except Guid.DoesNotExist:
                # fail if the guid doesn't exist
                print 'GUID {} DoesNotExist'.format(modm_node._id)
            else:
                # import ipdb; ipdb.set_trace()
                children = modm_node.get_descendants_recursive()
                kids = map(get_or_create_node, children)

                fk_nodes = process_node_fk_fields(modm_node)

                # m2m_nodes = process_node_m2m_fields(modm_node)

                fk_users = process_user_fk_fields(modm_node)

                m2m_users = process_user_m2m_fields(modm_node)

                m2m_tags = process_tag_m2m_fields(modm_node)

                node_fields = {}
                node_fields['_guid'] = guid
                node_fields.update(modm_node.to_storage())
                node_fields.update(fk_nodes)
                node_fields.update(fk_users)
                cleaned_node = {key: node_fields[key] for key in node_fields if key not in node_key_blacklist}
                for k, v in cleaned_node.iteritems():
                    if isinstance(v, datetime):
                        cleaned_node[k] = pytz.utc.localize(v)
                # this shouldn't need to be here, not sure why it has to be
                # if 'is_folder' in cleaned_node:
                #     cleaned_node['is_collection'] = cleaned_node.pop('is_folder')
                # if 'is_dashboard' in cleaned_node:
                #     cleaned_node['is_bookmark_collection'] = cleaned_node.pop('is_dashboard')
                # remove empty fields, sql angry, sql smash
                cleaned_node = {k: v for k, v in cleaned_node.iteritems() if v is not None}

                for fk_field in fk_node_fields + fk_user_fields:
                    if fk_field in cleaned_node.keys() and isinstance(cleaned_node[fk_field], basestring):
                        bad = cleaned_node.pop(fk_field)
                        print 'Removed {} {} from node {} because it no longer exists.'.format(fk_field, bad, guid.guid)

                node = Node.objects.create(**cleaned_node)
                global nodes
                nodes += 1
                # set_m2m_fields(node, m2m_nodes)
                set_m2m_fields(node, m2m_users)
                set_m2m_fields(node, m2m_tags)
        set_contributors(node, modm_node)
        all_of_the_things[modm_node._id] = node
    return node


def main():
    total = MODMNode.find().count()
    page_size = 1000
    count = 0
    print 'Doing {} Nodes...'.format(total)

    while count < total:
        for modm_node in MODMNode.find()[count:count+page_size]:
            noooood = get_or_create_node(modm_node)
            count += 1
            if count % page_size == 0:
                print 'Count: {}'.format(count)
                print 'Nodes: {}, Users: {}, Tags: {}'.format(nodes, users, tags)
                garbages = gc.collect()
                print 'Took out {} trashes.'.format(garbages)

    print 'MODM: {}'.format(total)
    print 'PG: {}'.format(count)
