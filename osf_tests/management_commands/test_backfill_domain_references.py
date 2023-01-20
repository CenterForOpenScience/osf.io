import mock
import pytest
from django.contrib.contenttypes.models import ContentType

from addons.wiki.tests.factories import WikiVersionFactory
from osf.management.commands import backfill_domain_references as backfill_task
from osf_tests.factories import (
    CommentFactory,
    NodeFactory,
    PreprintFactory,
    RegistrationFactory,
    UserFactory,
)
from osf.models.notable_domain import DomainReference, NotableDomain
from urllib.parse import urlparse


@pytest.mark.django_db
class TestBackfillDomainReferences:

    @pytest.fixture()
    def spam_domain(self):
        return urlparse('http://I-am-a-domain.io/with-a-path/?and=&query=parms')

    @pytest.fixture()
    def test_node(self, spam_domain):
        return NodeFactory(description=f'I am spam: {spam_domain.geturl()}', is_public=True)

    @pytest.fixture()
    def test_registration(self, spam_domain):
        return RegistrationFactory(description=f'I am spam: {spam_domain.geturl()}', is_public=True)

    @pytest.fixture()
    def test_comment(self, spam_domain):
        return CommentFactory(content=f'I am spam: {spam_domain.geturl()}')

    @pytest.fixture()
    def test_preprint(self, spam_domain):
        return PreprintFactory(description=f'I am spam: {spam_domain.geturl()}')

    @pytest.fixture()
    def test_wiki(self, spam_domain):
        return WikiVersionFactory(content=f'I am spam: {spam_domain.geturl()}')

    @pytest.fixture()
    def test_user(self, spam_domain):
        user = UserFactory()
        user.social['profileWebsites'] = [spam_domain.geturl()]
        user.save()
        return user

    @pytest.mark.enable_enqueue_task
    def test_backfill_project_domain_references(self, test_node, spam_domain):
        assert DomainReference.objects.count() == 0
        with mock.patch.object(backfill_task.spam_tasks.requests, 'head'):
            backfill_task.backfill_domain_references(model_name='osf.Node')

        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_node.id,
            referrer_content_type=ContentType.objects.get_for_model(test_node),
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_project_domain_references__wiki(self, test_wiki, spam_domain):
        assert DomainReference.objects.count() == 0
        with mock.patch.object(backfill_task.spam_tasks.requests, 'head'):
            backfill_task.backfill_domain_references(model_name='osf.Node')

        test_node = test_wiki.wiki_page.node
        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_node.id,
            referrer_content_type=ContentType.objects.get_for_model(test_node),
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_preprint_domain_references(self, test_preprint, spam_domain):
        assert DomainReference.objects.count() == 0
        with mock.patch.object(backfill_task.spam_tasks.requests, 'head'):
            backfill_task.backfill_domain_references(model_name='osf.Preprint')

        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_preprint.id,
            referrer_content_type=ContentType.objects.get_for_model(test_preprint)
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_registration_domain_references(self, test_registration, spam_domain):
        assert DomainReference.objects.count() == 0
        with mock.patch.object(backfill_task.spam_tasks.requests, 'head'):
            backfill_task.backfill_domain_references(model_name='osf.Registration')

        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_registration.id,
            referrer_content_type=ContentType.objects.get_for_model(test_registration)
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_comment_domain_references(self, test_comment, spam_domain):
        assert DomainReference.objects.count() == 0
        with mock.patch.object(backfill_task.spam_tasks.requests, 'head'):
            backfill_task.backfill_domain_references(model_name='osf.Comment')

        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_comment.id,
            referrer_content_type=ContentType.objects.get_for_model(test_comment)
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_user_domain_references(self, test_user, spam_domain):
        assert DomainReference.objects.count() == 0
        with mock.patch.object(backfill_task.spam_tasks.requests, 'head'):
            backfill_task.backfill_domain_references(model_name='osf.OSFUser')

        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_user.id,
            referrer_content_type=ContentType.objects.get_for_model(test_user)
        )
        assert created_reference.domain == domain
