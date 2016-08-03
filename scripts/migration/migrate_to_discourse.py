# There are three separate scripts used in migrating comments from the OSF to Discourse
# The first script is in the OSF, it can be run as
# (1) python -m scripts.migration.migrate_to_discourse export_file
# This file can then be imported to Discourse with
# (2) bundle exec ruby script/import_scripts/osf.rb export_file return_file
# which will create all of the users, categories, groups/projects, and topics
# that were exported from the osf. The return file contains id numbers for these
# various entities that the OSF will need to refer to them. These id numbers
# are then reimported back into the OSF with
# (3) python -m scripts.migration.migrate_from_discourse return_file
# Because the osf.rb import script does not exist in the actual discourse docker container
# The script will have to be manually added into script/import_scripts directory before executing

import os
import sys
import shutil
import tempfile
import json
import logging

from framework import discourse
from website import models, files
from website.addons import wiki
from website.app import init_app
from modularodm import Q

logger = logging.getLogger(__name__)

def serialize_users(file_out):
    users = models.User.find(Q('username', 'ne', None))

    data = {}
    data['type'] = 'count'
    data['object_type'] = 'user'
    data['count'] = users.count()

    logger.info('Serializing %i users' % data['count'])
    json.dump(data, file_out)
    file_out.write('\n')

    for user in users:
        data = {}
        data['email'] = user.username
        data['username'] = user._id
        data['name'] = user.fullname
        data['avatar_url'] = user.profile_image_url()
        data['is_disabled'] = user.is_disabled

        #logger.info('Serializing user %s' % user.fullname)
        json.dump(data, file_out)
        file_out.write('\n')

def serialize_projects(file_out, select_guids):
    data = {}
    data['type'] = 'count'
    data['object_type'] = 'project'
    data['count'] = len(select_guids)

    logger.info('Serializing %i projects' % data['count'])
    json.dump(data, file_out)
    file_out.write('\n')

    for guid in select_guids:
        project = models.Node.find_one(Q('_id', 'eq', guid))

        data = {}
        data['guid'] = project._id
        data['is_public'] = project.is_public
        contributors = [user._id for user in project.contributors if user.username]
        data['contributors'] = contributors
        data['is_deleted'] = project.is_deleted

        #logger.info('Serializing project %s' % project.label)
        json.dump(data, file_out)
        file_out.write('\n')

def serialize_comments(file_out):
    comments = models.Comment.find().sort('date_created')

    projects_needed = set()
    project_topics = set()
    file_topics = set()
    trashed_file_topics = set()
    wiki_topics = set()
    for comment in comments:
        comment_parent = comment.target.referent if comment.target else comment.node
        projects_needed.update(discourse.get_parent_guids(comment_parent))
        project_topics.update(discourse.get_parent_guids(comment_parent))
        if not isinstance(comment_parent, models.Node):
            projects_needed.add(comment_parent.node.guid_id)
            project_topics.add(comment_parent.node.guid_id)
            if isinstance(comment_parent, files.models.base.StoredFileNode):
                file_topics.add(comment_parent.guid_id)
            elif isinstance(comment_parent, files.models.base.TrashedFileNode):
                trashed_file_topics.add(comment_parent.guid_id)
            elif isinstance(comment_parent, wiki.model.NodeWikiPage):
                wiki_topics.add(comment_parent.guid_id)
    serialize_projects(file_out, projects_needed)

    data = {}
    data['type'] = 'count'
    data['object_type'] = 'post'
    data['count'] = len(project_topics) + len(file_topics) + len(trashed_file_topics) + len(wiki_topics) + comments.count()

    logger.info('Serializing %i project topics' % len(project_topics))
    logger.info('Serializing %i file topics' % len(file_topics))
    logger.info('Serializing %i trashed file topics' % len(trashed_file_topics))
    logger.info('Serializing %i wiki topics' % len(wiki_topics))
    logger.info('Serializing %i comments' % comments.count())
    json.dump(data, file_out)
    file_out.write('\n')

    serialized_topics = set()
    for comment in comments:
        comment_parent = comment.target.referent if comment.target else comment.node
        # Create a topic for each parent up to the top.
        next_parent = comment_parent
        while next_parent and not isinstance(next_parent, models.Comment) and next_parent.guid_id not in serialized_topics:
            data = {}
            data['post_type'] = 'topic'
            data['type'] = next_parent.target_type
            data['date_created'] = comment.date_created.isoformat()
            data['title'] = next_parent.label
            data['content'] = discourse.make_topic_content(next_parent)
            data['parent_guids'] = discourse.get_parent_guids(next_parent)
            data['topic_guid'] = next_parent.guid_id
            data['is_deleted'] = next_parent.is_deleted if next_parent.is_deleted is not None else False

            #logger.info('Serializing topic %s' % comment.node.label)
            json.dump(data, file_out)
            file_out.write('\n')

            # Don't serialize more than once, for multiple comments...
            serialized_topics.add(next_parent.guid_id)
            next_parent = next_parent.parent_node if isinstance(next_parent, models.Node) else next_parent.node

        data = {}
        data['post_type'] = 'comment'
        data['comment_guid'] = comment._id

        user = comment.user
        while user.is_merged:
            user = user.merged_by
        data['user'] = user._id

        data['content'] = comment.content
        data['date_created'] = comment.date_created.isoformat()
        if isinstance(comment_parent, models.Comment):
            data['reply_to'] = comment_parent._id
        else:
            data['reply_to'] = comment_parent.guid_id
        data['is_deleted'] = comment.is_deleted

        #logger.info('Serializing comment %s' % comment._id)
        json.dump(data, file_out)
        file_out.write('\n')

def main():
    if len(sys.argv) != 2:
        sys.exit('Usage: %s [output_file | --dry]' % sys.arv[0])

    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
        out_file = sys.stdout
        logger.warn('Dry_run mode')
    else:
        out_file = open(sys.argv[1], 'w')

    init_app(set_backends=True, routes=False)

    serialize_users(out_file)
    serialize_comments(out_file)

    if dry_run:
        print('')

if __name__ == '__main__':
    main()
