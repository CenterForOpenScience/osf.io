#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import datetime as dt
import mock
import httplib as http
from dateutil.parser import parse as parse_date

from nose.tools import *  # noqa PEP8 asserts

from modularodm import Q

from framework.exceptions import HTTPError
from framework.auth import Auth

from website.models import Node, MetaSchema, DraftRegistration
from website.project.metadata.schemas import ACTIVE_META_SCHEMAS, _name_to_id
from website.util import permissions, api_url_for
from website.project.views import drafts as draft_views

from tests.factories import (
    NodeFactory, AuthUserFactory, DraftRegistrationFactory, RegistrationFactory
)
from tests.test_registrations.base import RegistrationsTestBase

from tests.base import get_default_metaschema

class TestRegistrationViews(RegistrationsTestBase):

    def test_node_register_page_not_registration_redirects(self):
        url = self.node.web_url_for('node_register_page')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.FOUND)

    @mock.patch('website.archiver.tasks.archive')
    def test_node_register_page_registration(self, mock_archive):
        reg = self.node.register_node(get_default_metaschema(), self.auth, '', None)
        url = reg.web_url_for('node_register_page')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)

    def test_non_admin_can_view_node_register_page(self):
        non_admin = AuthUserFactory()
        self.node.add_contributor(
            non_admin,
            permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
            auth=self.auth,
            save=True
        )
        reg = RegistrationFactory(project=self.node)
        url = reg.web_url_for('node_register_page')
        res = self.app.get(url, auth=non_admin.auth)
        assert_equal(res.status_code, http.OK)

    def test_is_public_node_register_page(self):
        self.node.is_public = True
        self.node.save()
        reg = RegistrationFactory(project=self.node)
        reg.is_public = True
        reg.save()
        url = reg.web_url_for('node_register_page')
        res = self.app.get(url, auth=None)
        assert_equal(res.status_code, http.OK)

    @mock.patch('framework.tasks.handlers.enqueue_task', mock.Mock())
    def test_register_template_page_backwards_comptability(self):
        # Historically metaschema's were referenced by a slugified version
        # of their name.
        reg = self.draft.register(
            auth=self.auth,
            save=True
        )
        url = reg.web_url_for(
            'node_register_template_page',
            metaschema_id=_name_to_id(self.meta_schema.name),
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)

    def test_register_template_page_redirects_if_not_registration(self):
        url = self.node.web_url_for(
            'node_register_template_page',
            metaschema_id=self.meta_schema._id,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.FOUND)


class TestDraftRegistrationViews(RegistrationsTestBase):

    def tearDown(self):
        super(TestDraftRegistrationViews, self).tearDown()
        DraftRegistration.remove()

    def test_submit_draft_for_review(self):
        url = self.draft_api_url('submit_draft_for_review')
        res = self.app.post_json(
            url,
            self.embargo_payload,
            auth=self.user.auth
        )
        assert_equal(res.status_code, http.ACCEPTED)
        data = res.json
        assert_in('status', data)
        assert_equal(data['status'], 'initiated')

        self.draft.reload()
        assert_is_not_none(self.draft.approval)
        assert_equal(self.draft.approval.meta, {
            u'registration_choice': unicode(self.embargo_payload['registrationChoice']),
            u'embargo_end_date': unicode(self.embargo_payload['embargoEndDate'])
        })

    def test_submit_draft_for_review_invalid_registrationChoice(self):
        url = self.draft_api_url('submit_draft_for_review')
        res = self.app.post_json(
            url,
            self.invalid_payload,
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_submit_draft_for_review_already_registered(self):
        reg = RegistrationFactory(user=self.user)
        res = self.app.post_json(
            reg.api_url_for('submit_draft_for_review', draft_id=self.draft._id),
            self.invalid_payload,
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_draft_before_register_page(self):
        url = self.draft_url('draft_before_register_page')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)

    def test_submit_draft_for_review_non_admin(self):
        url = self.draft_api_url('submit_draft_for_review')
        res = self.app.post_json(
            url,
            self.embargo_payload,
            auth=self.non_admin.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.FORBIDDEN)

    @mock.patch('website.project.model.DraftRegistration.register', autospec=True)
    def test_register_draft_registration(self, mock_register_draft):

        url = self.node.api_url_for('register_draft_registration', draft_id=self.draft._id)
        res = self.app.post_json(url, {
            'registrationChoice': 'immediate'
        }, auth=self.user.auth)

        assert_equal(res.status_code, http.ACCEPTED)
        assert_equal(mock_register_draft.call_args[0][0]._id, self.draft._id)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_template_make_public_creates_pending_registration(self, mock_enquque):
        url = self.node.api_url_for('register_draft_registration', draft_id=self.draft._id)
        res = self.app.post_json(url, self.immediate_payload, auth=self.user.auth)

        assert_equal(res.status_code, http.ACCEPTED)
        self.node.reload()
        # Most recent node is a registration
        reg = Node.load(self.node.node__registrations[-1])
        assert_true(reg.is_registration)
        # The registration created is public
        assert_true(reg.is_pending_registration)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_template_make_public_makes_children_pending_registration(self, mock_enqueue):
        comp1 = NodeFactory(parent=self.node)
        NodeFactory(parent=comp1)

        url = self.node.api_url_for('register_draft_registration', draft_id=self.draft._id)
        res = self.app.post_json(url, self.immediate_payload, auth=self.user.auth)

        assert_equal(res.status_code, http.ACCEPTED)
        self.node.reload()
        # Most recent node is a registration
        reg = Node.load(self.node.node__registrations[-1])
        for node in reg.get_descendants_recursive():
            assert_true(node.is_registration)
            assert_true(node.is_pending_registration)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_draft_registration_with_embargo_creates_embargo(self, mock_enquque):
        url = self.node.api_url_for('register_draft_registration', draft_id=self.draft._id)
        end_date = dt.datetime.utcnow() + dt.timedelta(days=3)
        res = self.app.post_json(
            url,
            {
                'registrationChoice': 'embargo',
                'embargoEndDate': end_date.strftime('%c'),
            },
            auth=self.user.auth)

        assert_equal(res.status_code, http.ACCEPTED)
        self.node.reload()
        # Most recent node is a registration
        reg = Node.load(self.node.node__registrations[-1])
        assert_true(reg.is_registration)
        # The registration created is not public
        assert_false(reg.is_public)
        # The registration is pending an embargo that has not been approved
        assert_true(reg.is_pending_embargo)
        assert_false(reg.embargo_end_date)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_draft_registration_with_embargo_adds_to_parent_project_logs(self, mock_enquque):
        initial_project_logs = len(self.node.logs)
        res = self.app.post_json(
            self.node.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.embargo_payload,
            auth=self.user.auth
        )

        assert_equal(res.status_code, http.ACCEPTED)
        self.node.reload()
        # Logs: Created, registered, embargo initiated
        assert_equal(len(self.node.logs), initial_project_logs + 1)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_draft_registration_with_embargo_is_not_public(self, mock_enqueue):
        res = self.app.post_json(
            self.node.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.embargo_payload,
            auth=self.user.auth
        )

        assert_equal(res.status_code, http.ACCEPTED)

        registration = Node.find().sort('-registered_date')[0]

        assert_true(registration.is_registration)
        assert_false(registration.is_public)
        assert_true(registration.is_pending_embargo)
        assert_is_not_none(registration.embargo)

    @mock.patch('framework.tasks.handlers.enqueue_task')
    def test_register_draft_registration_invalid_embargo_end_date_raises_HTTPError(self, mock_enqueue):
        res = self.app.post_json(
            self.node.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.invalid_embargo_date_payload,
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_register_draft_registration_invalid_registrationChoice(self):
        res = self.app.post_json(
            self.node.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.invalid_payload,
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_register_draft_registration_already_registered(self):
        reg = RegistrationFactory(user=self.user)
        res = self.app.post_json(
            reg.api_url_for('register_draft_registration', draft_id=self.draft._id),
            self.invalid_payload,
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_get_draft_registration(self):
        url = self.draft_api_url('get_draft_registration')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        assert_equal(res.json['pk'], self.draft._id)

    def test_get_draft_registration_invalid(self):
        url = self.node.api_url_for('get_draft_registration', draft_id='13123123')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.NOT_FOUND)

    def test_get_draft_registration_not_admin(self):
        url = self.draft_api_url('get_draft_registration')
        res = self.app.get(url, auth=self.non_admin.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_get_draft_registrations_only_gets_drafts_for_that_node(self):
        dummy = NodeFactory()

        # Drafts for dummy node
        for i in range(5):
            d = DraftRegistrationFactory(
                initiator=self.user,
                branched_from=dummy,
                meta_schema=self.meta_schema,
                schema_data={}
            )

        found = [self.draft]
        # Drafts for self.node
        for i in range(3):
            d = DraftRegistrationFactory(
                initiator=self.user,
                branched_from=self.node,
                meta_schema=self.meta_schema,
                schema_data={}
            )
            found.append(d)
        url = self.node.api_url_for('get_draft_registrations')

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        # 3 new, 1 from setUp
        assert_equal(len(res.json['drafts']), 4)
        for draft in res.json['drafts']:
            assert_in(draft['pk'], [f._id for f in found])

    def test_new_draft_registration_POST(self):
        target = NodeFactory(creator=self.user)
        payload = {
            'schema_name': self.meta_schema.name,
            'schema_version': self.meta_schema.schema_version
        }
        url = target.web_url_for('new_draft_registration')

        res = self.app.post(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, http.FOUND)
        target.reload()
        draft = DraftRegistration.find_one(Q('branched_from', 'eq', target))
        assert_equal(draft.registration_schema, self.meta_schema)

    def test_new_draft_registration_on_registration(self):
        target = RegistrationFactory(user=self.user)
        payload = {
            'schema_name': self.meta_schema.name,
            'schema_version': self.meta_schema.schema_version
        }
        url = target.web_url_for('new_draft_registration')
        res = self.app.post(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_update_draft_registration_cant_update_registered(self):
        metadata = {
            'summary': {'value': 'updated'}
        }
        assert_not_equal(metadata, self.draft.registration_metadata)
        payload = {
            'schema_data': metadata,
            'schema_name': 'OSF-Standard Pre-Data Collection Registration',
            'schema_version': 1
        }
        self.draft.register(self.auth, save=True)
        url = self.node.api_url_for('update_draft_registration', draft_id=self.draft._id)

        res = self.app.put_json(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_edit_draft_registration_page_already_registered(self):
        self.draft.register(self.auth, save=True)
        url = self.node.web_url_for('edit_draft_registration_page', draft_id=self.draft._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_update_draft_registration(self):
        metadata = {
            'summary': {
                'value': 'updated',
                'comments': []
            }
        }
        assert_not_equal(metadata, self.draft.registration_metadata)
        payload = {
            'schema_data': metadata,
            'schema_name': 'OSF-Standard Pre-Data Collection Registration',
            'schema_version': 1
        }
        url = self.node.api_url_for('update_draft_registration', draft_id=self.draft._id)

        res = self.app.put_json(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)

        open_ended_schema = MetaSchema.find_one(
            Q('name', 'eq', 'OSF-Standard Pre-Data Collection Registration') &
            Q('schema_version', 'eq', 1)
        )
        self.draft.reload()
        assert_equal(open_ended_schema, self.draft.registration_schema)
        assert_equal(metadata, self.draft.registration_metadata)

    def test_update_draft_registration_non_admin(self):
        metadata = {
            'summary': {
                'value': 'updated',
                'comments': []
            }
        }
        assert_not_equal(metadata, self.draft.registration_metadata)
        payload = {
            'schema_data': metadata,
            'schema_name': 'OSF-Standard Pre-Data Collection Registration',
            'schema_version': 1
        }
        url = self.node.api_url_for('update_draft_registration', draft_id=self.draft._id)

        res = self.app.put_json(url, payload, auth=self.non_admin.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_delete_draft_registration(self):
        assert_equal(1, DraftRegistration.find().count())
        url = self.node.api_url_for('delete_draft_registration', draft_id=self.draft._id)

        res = self.app.delete(url, auth=self.user.auth)
        assert_equal(res.status_code, http.NO_CONTENT)
        assert_equal(0, DraftRegistration.find().count())

    def test_delete_draft_registration_non_admin(self):
        assert_equal(1, DraftRegistration.find().count())
        url = self.node.api_url_for('delete_draft_registration', draft_id=self.draft._id)

        res = self.app.delete(url, auth=self.non_admin.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)
        assert_equal(1, DraftRegistration.find().count())

    @mock.patch('website.archiver.tasks.archive')
    def test_delete_draft_registration_registered(self, mock_register_draft):
        self.draft.register(auth=self.auth, save=True)
        url = self.node.api_url_for('delete_draft_registration', draft_id=self.draft._id)

        res = self.app.delete(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    @mock.patch('website.archiver.tasks.archive')
    def test_delete_draft_registration_approved_and_registration_deleted(self, mock_register_draft):
        self.draft.register(auth=self.auth, save=True)
        self.draft.registered_node.is_deleted = True
        self.draft.registered_node.save()

        assert_equal(1, DraftRegistration.find().count())
        url = self.node.api_url_for('delete_draft_registration', draft_id=self.draft._id)

        res = self.app.delete(url, auth=self.user.auth)
        assert_equal(res.status_code, http.NO_CONTENT)
        assert_equal(0, DraftRegistration.find().count())

    def test_only_admin_can_delete_registration(self):
        non_admin = AuthUserFactory()
        assert_equal(1, DraftRegistration.find().count())
        url = self.node.api_url_for('delete_draft_registration', draft_id=self.draft._id)

        res = self.app.delete(url, auth=non_admin.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)
        assert_equal(1, DraftRegistration.find().count())

    def test_get_metaschemas(self):
        url = api_url_for('get_metaschemas')
        res = self.app.get(url).json
        assert_equal(len(res['meta_schemas']), len(ACTIVE_META_SCHEMAS))

    def test_get_metaschemas_all(self):
        url = api_url_for('get_metaschemas', include='all')
        res = self.app.get(url)
        assert_equal(res.status_code, http.OK)
        assert_equal(len(res.json['meta_schemas']), len(
            [
                schema for schema in MetaSchema.find()
                if schema.name in ACTIVE_META_SCHEMAS
            ]
        ))

    def test_validate_embargo_end_date_too_soon(self):
        today = dt.datetime.today()
        too_soon = today + dt.timedelta(days=5)
        try:
            draft_views.validate_embargo_end_date(too_soon.isoformat(), self.node)
        except HTTPError as e:
            assert_equal(e.code, http.BAD_REQUEST)
        else:
            self.fail()

    def test_validate_embargo_end_date_too_late(self):
        today = dt.datetime.today()
        too_late = today + dt.timedelta(days=(4 * 365) + 1)
        try:
            draft_views.validate_embargo_end_date(too_late.isoformat(), self.node)
        except HTTPError as e:
            assert_equal(e.code, http.BAD_REQUEST)
        else:
            self.fail()

    def test_validate_embargo_end_date_ok(self):
        today = dt.datetime.today()
        too_late = today + dt.timedelta(days=12)
        try:
            draft_views.validate_embargo_end_date(too_late.isoformat(), self.node)
        except Exception:
            self.fail()

    def test_check_draft_state_registered(self):
        reg = RegistrationFactory()
        self.draft.registered_node = reg
        self.draft.save()
        try:
            draft_views.check_draft_state(self.draft)
        except HTTPError as e:
            assert_equal(e.code, http.FORBIDDEN)
        else:
            self.fail()

    def test_check_draft_state_registered_but_deleted(self):
        reg = RegistrationFactory()
        self.draft.registered_node = reg
        reg.is_deleted = True
        self.draft.save()
        try:
            draft_views.check_draft_state(self.draft)
        except Exception:
            self.fail()

    def test_check_draft_state_pending_review(self):
        self.draft.submit_for_review(self.user, self.immediate_payload, save=True)
        try:
            with mock.patch.object(DraftRegistration, 'requires_approval', mock.PropertyMock(return_value=True)):
                draft_views.check_draft_state(self.draft)
        except HTTPError as e:
            assert_equal(e.code, http.FORBIDDEN)
        else:
            self.fail()

    def test_check_draft_state_approved(self):
        try:
            with mock.patch.object(DraftRegistration, 'requires_approval', mock.PropertyMock(return_value=True)), mock.patch.object(DraftRegistration, 'is_approved', mock.PropertyMock(return_value=True)):
                draft_views.check_draft_state(self.draft)
        except HTTPError as e:
            assert_equal(e.code, http.FORBIDDEN)
        else:
            self.fail()

    def test_check_draft_state_ok(self):
        try:
            draft_views.check_draft_state(self.draft)
        except Exception:
            self.fail()

    def test_check_draft_state_registered_and_deleted_and_approved(self):
        reg = RegistrationFactory()
        self.draft.registered_node = reg
        self.draft.save()
        reg.is_deleted = True
        reg.save()

        with mock.patch('website.project.model.DraftRegistration.is_approved', mock.PropertyMock(return_value=True)):
            try:
                draft_views.check_draft_state(self.draft)
            except HTTPError:
                self.fail()
