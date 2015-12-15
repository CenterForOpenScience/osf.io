# -*- coding: utf-8 -*-
import httplib as http
from modularodm import Q

from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group

from nose.tools import *  # flake8: noqa

from tests import factories
from tests.base import fake, AdminTestCase

from website.models import MetaSchema
from website.project.model import ensure_schemas

from admin.common_auth.models import MyUser as User
from admin.pre_reg.views import *  # noqa

PREREG_GROUP = Group.objects.get(name='prereg_group')


class PreregViewsTests(AdminTestCase):
    # urls = 'admin.pre_reg.urls'

    def setUp(self):
        super(PreregViewsTests, self).setUp()

        ensure_schemas()
        
        self.osf_user = factories.AuthUserFactory()
        password = fake.password(),
        self.user = User.objects.create(
            email=fake.email(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            osf_id=self.osf_user._id
        )
        self.user.set_password(password)
        self.user.save()
        self.logged_in = self.client.login(username=self.user.email, password=password)
        PREREG_GROUP.user_set.add(self.user)
        PREREG_GROUP.save()

        self.prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
        self.other_schema = MetaSchema.find(
            Q('name', 'ne', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )[0]

    def test_prereg(self):
        meta = {
            'q1': {
                'value': fake.sentence()
            }
        }
        
        node = factories.NodeFactory(creator=self.osf_user)
        prereg_pending = []
        for i in range(3):
            draft = factories.DraftRegistrationFactory(
                branched_from=node, 
                registration_schema=self.prereg_schema,
                registration_metadata=meta
            )
            draft.submit_for_review(
                self.osf_user, {
                    'registration_choice': 'immediate'
                },
                save=True
            )
            prereg_pending.append(draft)
        non_prereg_pending = []
        for i in range(3):            
            draft = factories.DraftRegistrationFactory(
                branched_from=node, 
                registration_schema=self.other_schema
            )
            draft.submit_for_review(
                self.osf_user, {
                    'registration_choice': 'immediate'
                },
                save=True
            )
            non_prereg_pending.append(draft)
        prereg_not_pending = []
        for i in range(3):
            draft = factories.DraftRegistrationFactory(
                branched_from=node, 
                registration_schema=self.prereg_schema
            )
            prereg_not_pending.append(draft)
        non_prereg_not_pending = []
        for i in range(3):            
            draft = factories.DraftRegistrationFactory(
                branched_from=node, 
                registration_schema=self.other_schema
            )
            non_prereg_not_pending.append(draft)
        
        url = reverse('pre_reg:prereg')        
        res = self.client.get(url)
        
        assert_equal(res.status_code, http.OK)
        assert_in('drafts', res.context)
        assert_equal(len(res.context['drafts']), len(prereg_pending))
        for draft in res.context['drafts']:
            assert_in(draft['pk'], [d._id for d in prereg_pending])
