# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
from nose.tools import *  # noqa (PEP8 asserts)
import mock

from website.models import MetaSchema

from tests.factories import (
    UserFactory, ApiOAuth2ApplicationFactory, NodeFactory, PointerFactory,
    ProjectFactory, NodeLogFactory, WatchConfigFactory,
    NodeWikiFactory, RegistrationFactory, UnregUserFactory,
    ProjectWithAddonFactory, UnconfirmedUserFactory, CommentFactory, PrivateLinkFactory,
    AuthUserFactory, DashboardFactory, FolderFactory,
    NodeLicenseRecordFactory, DraftRegistrationFactory
)
from tests.test_registrations.base import RegistrationsTestBase


class TestDraftRegistrations(RegistrationsTestBase):

    def test_factory(self):
        draft = DraftRegistrationFactory()
        assert_is_not_none(draft.branched_from)
        assert_is_not_none(draft.initiator)
        assert_is_not_none(draft.registration_schema)

        user = AuthUserFactory()
        draft = DraftRegistrationFactory(initiator=user)
        assert_equal(draft.initiator, user)

        node = ProjectFactory()
        draft = DraftRegistrationFactory(branched_from=node)
        assert_equal(draft.branched_from, node)
        assert_equal(draft.initiator, node.creator)

        schema = MetaSchema.find()[1]
        data = {'some': 'data'}
        draft = DraftRegistrationFactory(registration_schema=schema, registration_metadata=data)
        assert_equal(draft.registration_schema, schema)
        assert_equal(draft.registration_metadata, data)

    @mock.patch('website.project.model.Node.register_node')
    def test_register(self, mock_register_node):

        self.draft.register(self.auth)
        mock_register_node.assert_called_with(
            schema=self.draft.registration_schema,
            auth=self.auth,
            data=self.draft.registration_metadata,
        )

    def test_update_metadata_tracks_changes(self):
        self.draft.registration_metadata = {
            'foo': {
                'value': 'bar',
            },
            'a': {
                'value': 1,
            },
            'b': {
                'value': True
            },
        }
        changes =  self.draft.update_metadata({
            'foo': {
                'value': 'foobar',
            },
            'a': {
                'value': 1,
            },
            'b': {
                'value': True,
            },
            'c': {
                'value': 2,
            },
        })
        self.draft.save()
        for key in ['foo', 'c']:
            assert_in(key, changes)

    def test_update_metadata_handles_conflicting_comments(self):
        self.draft.registration_metadata = {
            'item01': {
                'value': 'foo',
                'comments': [{
                    'author': 'Bar',
                    'created': '1970-01-01T00:00:00.000Z',
                    'lastModified': '2015-08-05T14:58:30.574Z',
                    'value': 'qux'
                }]
            }
        }

        # outdated comment to be ignored
        changes1 = self.draft.update_metadata({
            'item01': {
                'value': 'foo',
                'comments': [{
                    'author': 'Bar',
                    'created': '1970-01-01T00:00:00.000Z',
                    'lastModified': '2015-07-05T14:58:30.574Z',
                    'value': 'foobarbaz'
                }]
            }
        })
        assert_equal(changes1, [])
        comment_one = self.draft.registration_metadata['item01']['comments'][0]
        assert_equal(comment_one.get('value'), 'qux')
        assert_equal(comment_one.get('author'), 'Bar')
        assert_equal(comment_one.get('created'), '1970-01-01T00:00:00.000Z')
        assert_equal(comment_one.get('lastModified'), '2015-08-05T14:58:30.574Z')

        self.draft.update_metadata({})

        # Totally new comment to be added
        self.draft.update_metadata({
            'item01': {
                'value': 'foo',
                'comments': [{
                    'author': 'Bar',
                    'created': '1970-01-01T00:00:00.000Z',
                    'lastModified': '2015-08-05T14:58:30.574Z',
                    'value': 'qux'},
                    {
                    'author': 'Baz',
                    'created': '1971-01-01T00:00:00.000Z',
                    'lastModified': '2014-07-09T14:58:30.574Z',
                    'value': 'foobarbaz'
                }]
            }
        })
        assert_equal(len(self.draft.registration_metadata['item01'].get('comments')), 2)
        comment_one = self.draft.registration_metadata['item01']['comments'][0]
        comment_two = self.draft.registration_metadata['item01']['comments'][1]

        assert_equal(comment_one.get('value'), 'qux')
        assert_equal(comment_one.get('author'), 'Bar')
        assert_equal(comment_one.get('created'), '1970-01-01T00:00:00.000Z')
        assert_equal(comment_one.get('lastModified'), '2015-08-05T14:58:30.574Z')

        assert_equal(comment_two.get('value'), 'foobarbaz')
        assert_equal(comment_two.get('author'), 'Baz')
        assert_equal(comment_two.get('created'), '1971-01-01T00:00:00.000Z')
        assert_equal(comment_two.get('lastModified'), '2014-07-09T14:58:30.574Z')


class TestPreregFunctionality(RegistrationsTestBase):

    def test_on_complete(self):
        pass

