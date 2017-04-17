from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from website.util import permissions

from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
)

from api_tests import utils as test_utils

class PreprintIsPublishedListMixin(object):

    def setUp(self):
        super(PreprintIsPublishedListMixin, self).setUp()
        assert self.admin, 'Subclasses of PreprintIsPublishedMixin must define self.admin'
        assert self.provider_one, 'Subclasses of PreprintIsPublishedMixin must define self.provider_one'
        assert self.provider_two, 'Subclasses of PreprintIsPublishedMixin must define self.provider_two'
        assert self.published_project, 'Subclasses of PreprintIsPublishedMixin must define self.published_project'
        assert self.public_project, 'Subclasses of PreprintIsPublishedMixin must define self.public_project'
        assert self.url, 'Subclasses of PreprintIsPublishedMixin must define self.url'

        self.write_contrib = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

        self.public_project.add_contributor(self.write_contrib, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        self.subject = SubjectFactory()

        self.file_one_public_project = test_utils.create_test_file(self.public_project, self.admin, 'mgla.pdf')
        self.file_one_published_project = test_utils.create_test_file(self.published_project, self.admin, 'saor.pdf')

        self.unpublished_preprint = PreprintFactory(creator=self.admin, filename='mgla.pdf', provider=self.provider_one, subjects=[[self.subject._id]], project=self.public_project, is_published=False)
        self.published_preprint = PreprintFactory(creator=self.admin, filename='saor.pdf', provider=self.provider_two, subjects=[[self.subject._id]], project=self.published_project, is_published=True)

    def test_unpublished_visible_to_admins(self):
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 2
        assert self.unpublished_preprint._id in [d['id'] for d in res.json['data']]

    def test_unpublished_invisible_to_write_contribs(self):
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 1
        assert self.unpublished_preprint._id not in [d['id'] for d in res.json['data']]

    def test_unpublished_invisible_to_non_contribs(self):
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 1
        assert self.unpublished_preprint._id not in [d['id'] for d in res.json['data']]

    def test_unpublished_invisible_to_public(self):
        res = self.app.get(self.url)
        assert len(res.json['data']) == 1
        assert self.unpublished_preprint._id not in [d['id'] for d in res.json['data']]

    def test_filter_published_false_admin(self):
        res = self.app.get('{}filter[is_published]=false'.format(self.url), auth=self.admin.auth)
        assert len(res.json['data']) == 1
        assert self.unpublished_preprint._id in [d['id'] for d in res.json['data']]

    def test_filter_published_false_write_contrib(self):
        res = self.app.get('{}filter[is_published]=false'.format(self.url), auth=self.write_contrib.auth)
        assert len(res.json['data']) == 0

    def test_filter_published_false_non_contrib(self):
        res = self.app.get('{}filter[is_published]=false'.format(self.url), auth=self.non_contrib.auth)
        assert len(res.json['data']) == 0

    def test_filter_published_false_public(self):
        res = self.app.get('{}filter[is_published]=false'.format(self.url))
        assert len(res.json['data']) == 0

class PreprintIsValidListMixin(object):

    def setUp(self):
        super(PreprintIsValidListMixin, self).setUp()
        assert self.admin, 'Subclasses of PreprintIsValidListMixin must define self.admin'
        assert self.project, 'Subclasses of PreprintIsValidListMixin must define self.project'
        assert self.provider, 'Subclasses of PreprintIsValidListMixin must define self.provider'
        assert self.url, 'Subclasses of PreprintIsValidListMixin must define self.url'

        self.write_contrib = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

        self.subject = SubjectFactory()
        self.file_one_project = test_utils.create_test_file(self.project, self.admin, 'saor.pdf')
        self.project.add_contributor(self.write_contrib, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        self.preprint = PreprintFactory(creator=self.admin, filename='saor.pdf', provider=self.provider, subjects=[[self.subject._id]], project=self.project, is_published=True)

    # Test private
    def test_preprint_private_invisible_no_auth(self):
        res = self.app.get(self.url)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url)
        assert len(res.json['data']) == 0

    def test_preprint_private_invisible_non_contributor(self):
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 0

    def test_preprint_private_visible_write(self):
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 1

    def test_preprint_private_visible_owner(self):
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 1

    def test_preprint_node_deleted_invisible(self):
        self.project.is_deleted = True
        self.project.save()
        # no auth
        res = self.app.get(self.url)
        assert len(res.json['data']) == 0
        # contrib
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 0
        # write_contrib
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 0
        # admin
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 0

    def test_preprint_node_null_invisible(self):
        self.preprint.node = None
        self.preprint.save()
        # no auth
        res = self.app.get(self.url)
        assert len(res.json['data']) == 0
        # contrib
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 0
        # write_contrib
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 0
        # admin
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 0
