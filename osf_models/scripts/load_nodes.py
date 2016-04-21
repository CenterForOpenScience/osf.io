from website.app import init_app

init_app()

# MIGRATE NODES

from website.models import Node as MODMNode
from website.models import Tag as MODMTag
from modularodm import Q
from osf_models.models import Node, User, Tag, Guid, Contributor
import pytz
from datetime import datetime

fk_node_fields = [
    'forked_from',
    'registered_from',
    'root',
    'parent_node',
    'template_node'
]
m2m_node_fields = [
    'nodes',
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
    'contributors'
]
m2m_tag_fields = [
    'tags',
    'system_tags'
]

node_cache = {
    # 'xyz12': {
    #     'modm': modm_object,
    #     'django': django_object,
    # }
}
user_cache = []
tag_cache = []

node_key_blacklist = [
                         '__backrefs',
                         '_version',
                         'expanded',
                         # foreign keys not yet implemented
                         'logs',
                         'primary_institution',
                         'registration_approval',
                         'alternative_citations',
                         'registered_schema',
                         'affiliated_institutions',
                         'retraction',
                         'embargo',
                         'node_license',
                     ] + m2m_node_fields + m2m_user_fields + m2m_tag_fields
user_key_blacklist = ['__backrefs', '_version', 'affiliated_institutions', 'watched',
                      'external_accounts', ] + m2m_node_fields + m2m_user_fields + m2m_tag_fields

tag_key_blacklist = ['_version', '__backrefs', ] + m2m_node_fields + m2m_user_fields + m2m_tag_fields


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
                    if m2m_node_field in m2m_nodes:
                        node = get_or_create_node(nv)
                        if node is not None:
                            m2m_nodes[m2m_node_field].append(node)
                        else:
                            m2m_nodes[m2m_node_field] = [node, ]
            else:
                if m2m_node_field in m2m_nodes:
                    node = get_or_create_node(value)
                    if node is not None:
                        m2m_nodes[m2m_node_field].append(node)
                    else:
                        m2m_nodes[m2m_node_field] = [node, ]
    return m2m_nodes


def process_user_fk_fields(modm_object):
    fk_users = {}
    for fk_user_field in fk_user_fields:
        modm_user = getattr(modm_object, fk_user_field, None)
        if modm_user is not None:
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
                if m2m_user_field in m2m_users:
                    user = get_or_create_user(uv)
                    if user is not None:
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
    try:
        user = User.objects.get(_guid__guid=modm_user._id)
    except User.DoesNotExist:
        user_fk_nodes = process_node_fk_fields(modm_user)
        user_m2m_nodes = process_node_m2m_fields(modm_user)
        user_fk_users = process_user_fk_fields(modm_user)
        user_m2m_users = process_user_m2m_fields(modm_user)
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
        set_m2m_fields(user, user_m2m_nodes)
        set_m2m_fields(user, user_m2m_users)
        set_m2m_fields(user, user_m2m_tags)
    user_cache.append(user)
    return user


def get_or_create_tag(modm_tag, system=False):
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
    tag_cache.append(tag)
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
            fk_nodes = process_node_fk_fields(modm_node)

            m2m_nodes = process_node_m2m_fields(modm_node)

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
            cleaned_node['is_collection'] = cleaned_node.pop('is_folder')
            cleaned_node['is_bookmark_collection'] = cleaned_node.pop('is_dashboard')
            # remove empty fields, sql angry, sql smash
            cleaned_node = {k: v for k, v in cleaned_node.iteritems() if v is not None}

            for fk_field in fk_node_fields + fk_user_fields:
                if fk_field in cleaned_node.keys() and isinstance(cleaned_node[fk_field], basestring):
                    bad = cleaned_node.pop(fk_field)
                    print 'Removed {} {} from node {} because it no longer exists.'.format(fk_field, bad, guid.guid)

            node = Node.objects.create(**cleaned_node)
            set_m2m_fields(node, m2m_nodes)
            set_m2m_fields(node, m2m_users)
            set_m2m_fields(node, m2m_tags)
    set_contributors(node, modm_node)
    if modm_node._id not in node_cache:
        node_cache[modm_node._id] = dict()
    node_cache[modm_node._id]['django'] = node
    return node


def main():
    modm_nodes = MODMNode.find()[19000:]

    total = len(modm_nodes)
    count = 0
    print 'Doing {} Nodes...'.format(total)

    for modm_node in modm_nodes:
        node_cache[modm_node._id] = {'modm': modm_node}
        noooood = get_or_create_node(modm_node)
        count += 1
        if count % 1000 == 0:
            print count

    print 'Nodes: {}'.format(len(node_cache))
    print 'Users: {}'.format(len(user_cache))
    print 'Tags: {}'.format(len(tag_cache))

    print 'MODM: {}'.format(total)
    print 'PG: {}'.format(count)
