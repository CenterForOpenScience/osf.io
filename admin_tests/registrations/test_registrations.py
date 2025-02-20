from scripts.approve_registrations import main as approve_registrations_runner
from datetime import timedelta
import pytest
from osf_tests.factories import AuthUserFactory, ProjectFactory, RegistrationFactory


@pytest.mark.django_db
class TestRegistrationSpamHam:

    @pytest.fixture()
    def superuser(self):
        superuser = AuthUserFactory()
        superuser.is_superuser = True
        superuser.save()
        return superuser

    @pytest.fixture()
    def public_project(self, superuser):
        return ProjectFactory(title='Public Project', is_public=True, creator=superuser)

    @pytest.fixture()
    def private_project(self, superuser):
        return ProjectFactory(title='Private Project', is_public=False, creator=superuser)

    @pytest.fixture()
    def private_project_from_public(self, public_project):
        public_project.set_privacy('private', save=True)
        return public_project

    @pytest.fixture()
    def public_project_from_private(self, private_project):
        private_project.set_privacy('public', save=True)
        return private_project

    @pytest.fixture()
    def public_registration_from_public_project(self, superuser, public_project):
        return RegistrationFactory(project=public_project, creator=superuser, is_public=True)

    @pytest.fixture()
    def public_registration_from_private_project(self, superuser, private_project):
        return RegistrationFactory(project=private_project, creator=superuser, is_public=True)

    @pytest.fixture()
    def private_registration_from_public_project(self, superuser, public_project):
        return RegistrationFactory(project=public_project, creator=superuser, is_public=False)

    @pytest.fixture()
    def public_registration_from_changed_to_public_project(self, superuser, public_project_from_private):
        return RegistrationFactory(project=public_project_from_private, creator=superuser, is_public=True)

    @pytest.fixture()
    def public_registration_from_changed_to_private_project(self, superuser, private_project_from_public):
        return RegistrationFactory(project=private_project_from_public, creator=superuser, is_public=True)

    @pytest.fixture()
    def embargoed_registration_from_public_project(self, superuser, public_project):
        return RegistrationFactory(project=public_project, creator=superuser, is_embargoed=True)

    @pytest.fixture()
    def embargoed_registration_from_private_project(self, superuser, private_project):
        return RegistrationFactory(project=private_project, creator=superuser, is_embargoed=True)

    @pytest.fixture()
    def embargoed_registration_from_changed_to_public_project(self, superuser, public_project_from_private):
        return RegistrationFactory(project=public_project_from_private, creator=superuser, is_embargoed=True)

    @pytest.fixture()
    def embargoed_registration_from_changed_to_private_project(self, superuser, private_project_from_public):
        return RegistrationFactory(project=private_project_from_public, creator=superuser, is_embargoed=True)

    def test_embargoed_registration_from_public_project_spam_ham(self, embargoed_registration_from_public_project):
        embargoed_registration_from_public_project.confirm_spam(save=True)
        assert not embargoed_registration_from_public_project.is_public
        embargoed_registration_from_public_project.confirm_ham(save=True)
        assert not embargoed_registration_from_public_project.is_public

    def test_embargoed_registration_from_private_project_spam_ham(self, embargoed_registration_from_private_project):
        embargoed_registration_from_private_project.confirm_spam(save=True)
        assert not embargoed_registration_from_private_project.is_public
        embargoed_registration_from_private_project.confirm_ham(save=True)
        assert not embargoed_registration_from_private_project.is_public

    def test_embargoed_registration_from_changed_to_public_project_spam_ham(self, embargoed_registration_from_changed_to_public_project):
        embargoed_registration_from_changed_to_public_project.confirm_spam(save=True)
        assert not embargoed_registration_from_changed_to_public_project.is_public
        embargoed_registration_from_changed_to_public_project.confirm_ham(save=True)
        assert not embargoed_registration_from_changed_to_public_project.is_public

    def test_embargoed_registration_from_changed_to_private_project_spam_ham(self, embargoed_registration_from_changed_to_private_project):
        embargoed_registration_from_changed_to_private_project.confirm_spam(save=True)
        assert not embargoed_registration_from_changed_to_private_project.is_public
        embargoed_registration_from_changed_to_private_project.confirm_ham(save=True)
        assert not embargoed_registration_from_changed_to_private_project.is_public

    def test_public_registration_from_public_project_spam_ham(self, superuser, public_registration_from_public_project):
        public_registration_from_public_project.confirm_spam(save=True)
        assert not public_registration_from_public_project.is_public
        public_registration_from_public_project.confirm_ham(save=True)
        assert public_registration_from_public_project.is_public

    def test_public_registration_from_private_project_spam_ham(self, superuser, public_registration_from_private_project):
        public_registration_from_private_project.confirm_spam(save=True)
        assert not public_registration_from_private_project.is_public
        public_registration_from_private_project.confirm_ham(save=True)
        assert public_registration_from_private_project.is_public

    def test_private_registration_from_private_project_spam_ham(self, superuser, private_registration_from_public_project):
        private_registration_from_public_project.confirm_spam(save=True)
        assert not private_registration_from_public_project.is_public
        private_registration_from_public_project.confirm_ham(save=True)
        assert not private_registration_from_public_project.is_public

    def test_public_registration_from_changed_to_public_project_spam_ham(self, superuser, public_registration_from_changed_to_public_project):
        public_registration_from_changed_to_public_project.confirm_spam(save=True)
        assert not public_registration_from_changed_to_public_project.is_public
        public_registration_from_changed_to_public_project.confirm_ham(save=True)
        assert public_registration_from_changed_to_public_project.is_public

    def test_public_registration_from_changed_to_private_project_spam_ham(self, superuser, public_registration_from_changed_to_private_project):
        public_registration_from_changed_to_private_project.confirm_spam(save=True)
        assert not public_registration_from_changed_to_private_project.is_public
        public_registration_from_changed_to_private_project.confirm_ham(save=True)
        assert public_registration_from_changed_to_private_project.is_public

    def test_unapproved_registration_task(self, embargoed_registration_from_changed_to_public_project):
        embargoed_registration_from_changed_to_public_project.registration_approval.state = 'unapproved'
        embargoed_registration_from_changed_to_public_project.registration_approval.initiation_date -= timedelta(3)
        embargoed_registration_from_changed_to_public_project.registration_approval.save()
        assert embargoed_registration_from_changed_to_public_project.registration_approval.state == 'unapproved'
        approve_registrations_runner(dry_run=False)
        embargoed_registration_from_changed_to_public_project.registration_approval.refresh_from_db()
        assert embargoed_registration_from_changed_to_public_project.registration_approval.state == 'approved'

    def test_unapproved_registration_task_after_spam(self, embargoed_registration_from_changed_to_public_project):
        embargoed_registration_from_changed_to_public_project.registration_approval.state = 'unapproved'
        embargoed_registration_from_changed_to_public_project.registration_approval.initiation_date -= timedelta(3)
        embargoed_registration_from_changed_to_public_project.registration_approval.save()
        embargoed_registration_from_changed_to_public_project.confirm_spam(save=True)
        assert embargoed_registration_from_changed_to_public_project.registration_approval.state == 'unapproved'
        approve_registrations_runner(dry_run=False)
        embargoed_registration_from_changed_to_public_project.registration_approval.refresh_from_db()
        assert embargoed_registration_from_changed_to_public_project.registration_approval.state == 'unapproved'

    def test_unapproved_registration_task_after_spam_ham(self, embargoed_registration_from_changed_to_public_project):
        embargoed_registration_from_changed_to_public_project.registration_approval.state = 'unapproved'
        embargoed_registration_from_changed_to_public_project.registration_approval.initiation_date -= timedelta(3)
        embargoed_registration_from_changed_to_public_project.registration_approval.save()
        embargoed_registration_from_changed_to_public_project.confirm_spam(save=True)
        embargoed_registration_from_changed_to_public_project.confirm_ham(save=True)
        assert embargoed_registration_from_changed_to_public_project.registration_approval.state == 'unapproved'
        approve_registrations_runner(dry_run=False)
        embargoed_registration_from_changed_to_public_project.registration_approval.refresh_from_db()
        assert embargoed_registration_from_changed_to_public_project.registration_approval.state == 'approved'
