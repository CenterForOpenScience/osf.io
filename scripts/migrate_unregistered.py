#!/usr/bin/env
# -*- coding: utf-8 -*-
"""Migrates old-style unregistered users (dictionaries in Node#contributor_list)
to actual User records.
"""
import logging

from modularodm.exceptions import ValidationValueError
from website import app, models
from framework import auth
from framework.auth.decorators import Auth
from tests.base import OsfTestCase
from tests.factories import DeprecatedUnregUserFactory, ProjectFactory, UserFactory


logging.getLogger('factory.generate:BaseFactory').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main():
    app.init_app()
    for node in models.Node.find():
        migrate_contributors(node)


def make_user(user_dict):
    if 'id' in user_dict:
        user = models.User.load(user_dict['id'])
    else:
        name, email = user_dict['nr_name'], user_dict['nr_email']
        try:
            user = models.User.create_unregistered(fullname=name,
                email=email)
            user.save()
        except ValidationValueError:
            user = auth.get_user(username=email)
            if user is None:
                logger.error('Could not load user {0}'.format(user_dict))
    return user


def migrate_user(user_dict, node):
    user = make_user(user_dict)
    if user is None:
        logger.error('Could not load user {0}'.format(user_dict))
        return
    # Add unclaimed_record to unregistered users for a given node
    if not user.is_registered:
        # First contributor (usually the creator) will be recorded as the referrer
        # of unregistered users
        try:
            referrer = node.contributors[0]
        except IndexError:
            if node.creator:
                referrer = node.creator
            else:  # meh
                return
        user.add_unclaimed_record(node=node, referrer=referrer,
            given_name=user_dict['nr_name'], email=user_dict['nr_email'])
        logger.info(u'Migrated unregistered user {0}'.format(user.username))
        try:
            user.save()
        except Exception as error:
            logging.error(user_dict)
            raise error
    return user


def migrate_contributors(node):
    node.contributors = [
        migrate_user(user_dict, node) for user_dict in node.contributor_list

    ]
    logger.info(u'Finished migrating unregistered '
        'contributors for node {0}'.format(node._primary_key))
    return node.save()

# To run tests: pytest scripts/migrate_unregistered.py
# or nosetests scripts/migrate_unregistered.py
class TestMigratingUnreg(OsfTestCase):

    def test_make_user_from_reg_user(self):
        reg_user = UserFactory(is_registered=True)
        user = make_user({'id': reg_user._primary_key})
        assert user == reg_user

    def test_make_user_from_old_unreg_user(self):
        old_style = DeprecatedUnregUserFactory()
        user = make_user(old_style)
        user.save()
        assert isinstance(user, models.User)
        assert user.is_registered is False
        assert user.fullname == old_style['nr_name']
        assert user.username == old_style['nr_email']
        assert old_style['nr_email'] in user.emails

    def test_migrate_contributors(self):
        creator = UserFactory(is_registered=True)
        project = ProjectFactory(creator=creator)
        auth = Auth(project.creator)

        contrib1 = UserFactory()
        project.add_contributor(contrib1, auth=auth)
        project.save()
        # sanity checks
        assert len(project.contributor_list) == 2

        nr_contrib = DeprecatedUnregUserFactory()
        project.contributor_list.append(nr_contrib)
        project.save()
        assert len(project.contributors) == 2
        assert len(project.contributor_list) == 3
        old_length = len(project.contributor_list)

        migrate_contributors(project)
        project.save()

        assert len(project.contributor_list) == old_length
        assert len(project.contributors) == old_length

        migrated_user = project.contributors[-1]
        assert migrated_user.fullname == nr_contrib['nr_name']
        assert migrated_user.is_registered is False

        # has an unclaimed record
        assert project._primary_key in migrated_user.unclaimed_records
        rec = migrated_user.get_unclaimed_record(project._primary_key)
        assert rec['name'] == nr_contrib['nr_name']
        assert rec['referrer_id'] == creator._primary_key
        assert rec['token']
        assert rec['email'] == nr_contrib['nr_email']

    def test_migrate_nr_user_with_same_email_as_registered_user(self):
        reg_user = UserFactory(is_registered=True)

        unreg_user = DeprecatedUnregUserFactory(nr_email=reg_user.username)

        assert make_user(unreg_user) == reg_user


if __name__ == '__main__':
    main()
