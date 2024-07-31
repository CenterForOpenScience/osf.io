import logging

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
from osf.models import Node, Preprint, Registration
from osf.models.notable_domain import DomainReference, NotableDomain
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@pytest.mark.django_db
class TestBackfillDomainReferences:

    @pytest.fixture()
    def spam_domain(self):
        return urlparse('http://I-am-a-domain.io/with-a-path/?and=&query=parms')

    @pytest.fixture()
    def test_node(self, spam_domain, request):
        return NodeFactory(is_public=True, description=f'I am spam: {spam_domain.geturl()}')

    @pytest.fixture()
    def test_registration(self, spam_domain, request):
        return RegistrationFactory(is_public=True, description=f'I am spam: {spam_domain.geturl()}')

    @pytest.fixture()
    def test_comment(self, spam_domain):
        return CommentFactory(content=f'I am spam: {spam_domain.geturl()}')

    @pytest.fixture()
    def test_preprint(self, spam_domain, request):
        return PreprintFactory(description=f'I am spam: {spam_domain.geturl()}')

    @pytest.fixture()
    def test_wiki(self, spam_domain):
        return WikiVersionFactory(content=f'I am spam: {spam_domain.geturl()}')

    @pytest.fixture()
    def test_user(self, spam_domain, mock_spam_head_request):
        user = UserFactory()
        user.social['profileWebsites'] = [spam_domain.geturl()]
        user.save()
        return user

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('spam_check_field', sorted(Node.SPAM_CHECK_FIELDS))
    def test_backfill_project_domain_references(self, spam_check_field, spam_domain, mock_spam_head_request):
        test_node = NodeFactory(is_public=True)
        setattr(test_node, spam_check_field, f'I am spam: {spam_domain.geturl()}')
        test_node.save()

        assert DomainReference.objects.count() == 0
        backfill_task.backfill_domain_references(model_name='osf.Node')

        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_node.id,
            referrer_content_type=ContentType.objects.get_for_model(test_node),
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_project_domain_references__only_selected_once(self, test_node, mock_spam_head_request):
        initial_resource_count = backfill_task.backfill_domain_references(model_name='osf.Node')
        subsequent_resource_count = backfill_task.backfill_domain_references(model_name='osf.Node')

        assert initial_resource_count == 1
        assert subsequent_resource_count == 0

    @pytest.mark.enable_enqueue_task
    def test_backfill_project_domain_references__resources_without_domains_ignored(self, test_node, mock_spam_head_request):
        # Node without links
        NodeFactory(is_public=True, description='No URIs here!')
        resource_count = backfill_task.backfill_domain_references(model_name='osf.Node')
        # Just the test_node retrieved
        assert resource_count == 1

    @pytest.mark.enable_enqueue_task
    def test_backfill_project_domain_references__wiki(self, test_wiki, spam_domain, mock_spam_head_request):
        assert DomainReference.objects.count() == 0
        backfill_task.backfill_domain_references(model_name='osf.Node')

        test_node = test_wiki.wiki_page.node
        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_node.id,
            referrer_content_type=ContentType.objects.get_for_model(test_node),
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_project_domain_references__wiki__no_dupes_with_multiple_versions(self, test_wiki, mock_spam_head_request):
        node = test_wiki.wiki_page.node
        node.description = 'Blah blah blah blah blah blah https://www.osf.io'
        node.save()
        WikiVersionFactory(
            wiki_page=test_wiki.wiki_page,
            content='Innocuous link: https://google.com repeated link: osf.io'
        )

        resource_count = backfill_task.backfill_domain_references(model_name='osf.Node')

        assert resource_count == 1
        assert DomainReference.objects.filter(
            referrer_object_id=node.id,
            referrer_content_type=ContentType.objects.get_for_model(Node),
        ).count() == 3

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('spam_check_field', sorted(Preprint.SPAM_CHECK_FIELDS))
    def test_backfill_preprint_domain_references(self, spam_check_field, spam_domain, mock_spam_head_request):
        test_preprint = PreprintFactory()
        setattr(test_preprint, spam_check_field, f'I am spam: {spam_domain.geturl()}')
        test_preprint.save()

        assert DomainReference.objects.count() == 0
        backfill_task.backfill_domain_references(model_name='osf.Preprint')

        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_preprint.id,
            referrer_content_type=ContentType.objects.get_for_model(test_preprint)
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_preprint_domain_references__only_selected_once(self, test_preprint, mock_spam_head_request):
        initial_resource_count = backfill_task.backfill_domain_references(model_name='osf.Preprint')
        subsequent_resource_count = backfill_task.backfill_domain_references(model_name='osf.Preprint')
        assert initial_resource_count == 1
        assert subsequent_resource_count == 0

    @pytest.mark.enable_enqueue_task
    def test_backfill_preprint_domain_references__resources_without_domains_ignored(self, test_preprint, mock_spam_head_request):
        # Preprint without links
        PreprintFactory(is_public=True, description='No URIs here!')
        resource_count = backfill_task.backfill_domain_references(model_name='osf.Preprint')
        # Just the test_preprint retrieved
        assert resource_count == 1

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('spam_check_field', sorted(Registration.SPAM_CHECK_FIELDS))
    def test_backfill_registration_domain_references(self, spam_check_field, spam_domain, mock_spam_head_request):
        test_registration = RegistrationFactory(is_public=True)
        setattr(test_registration, spam_check_field, f'I am spam: {spam_domain.geturl()}')
        test_registration.save()

        assert DomainReference.objects.count() == 0
        backfill_task.backfill_domain_references(model_name='osf.Registration')

        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_registration.id,
            referrer_content_type=ContentType.objects.get_for_model(test_registration)
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_registration_domain_references__only_selected_once(self, test_registration, mock_spam_head_request):
        initial_resource_count = backfill_task.backfill_domain_references(model_name='osf.Registration')
        subsequent_resource_count = backfill_task.backfill_domain_references(model_name='osf.Registration')
        assert initial_resource_count == 1
        assert subsequent_resource_count == 0

    @pytest.mark.enable_enqueue_task
    def test_backfill_registration_domain_references__resources_without_domains_ignored(self, test_registration, mock_spam_head_request):
        # Registration without links
        RegistrationFactory(is_public=True, description='No URIs here!')
        resource_count = backfill_task.backfill_domain_references(model_name='osf.Registration')
        # Just the test_registration retrieved
        assert resource_count == 1

    @pytest.mark.enable_enqueue_task
    def test_backfill_comment_domain_references(self, test_comment, spam_domain, mock_spam_head_request):
        assert DomainReference.objects.count() == 0
        backfill_task.backfill_domain_references(model_name='osf.Comment')

        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_comment.id,
            referrer_content_type=ContentType.objects.get_for_model(test_comment)
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_comment_domain_references__only_selected_once(self, test_comment, mock_spam_head_request):
        initial_resource_count = backfill_task.backfill_domain_references(model_name='osf.Comment')
        subsequent_resource_count = backfill_task.backfill_domain_references(model_name='osf.Comment')
        assert initial_resource_count == 1
        assert subsequent_resource_count == 0

    @pytest.mark.enable_enqueue_task
    def test_backfill_comment_domain_references__resources_without_domains_ignored(self, test_comment, mock_spam_head_request):
        # Comment without links
        CommentFactory(content='No URIs here!')
        resource_count = backfill_task.backfill_domain_references(model_name='osf.Comment')
        # Just the test_comment retrieved
        assert resource_count == 1

    @pytest.mark.enable_enqueue_task
    def test_backfill_user_domain_references(self, test_user, spam_domain, mock_spam_head_request):
        # delete DomainReference's created on test_user save()
        DomainReference.objects.all().delete()
        assert DomainReference.objects.count() == 0
        backfill_task.backfill_domain_references(model_name='osf.OSFUser')

        domain = NotableDomain.objects.get(domain=spam_domain.netloc)
        created_reference = DomainReference.objects.get(
            referrer_object_id=test_user.id,
            referrer_content_type=ContentType.objects.get_for_model(test_user)
        )
        assert created_reference.domain == domain

    @pytest.mark.enable_enqueue_task
    def test_backfill_user_domain_references__only_selected_once(self, test_user, mock_spam_head_request):
        # Delete domains created on user save to simulate a backfill
        NotableDomain.objects.all().delete()

        initial_resource_count = backfill_task.backfill_domain_references(model_name='osf.OSFUser')
        subsequent_resource_count = backfill_task.backfill_domain_references(model_name='osf.OSFUser')
        assert initial_resource_count == 1
        assert subsequent_resource_count == 0

    @pytest.mark.enable_enqueue_task
    def test_backfill_user_domain_references__resources_without_domains_ignored(self, test_user, spam_domain, mock_spam_head_request):
        # Delete domains created on user save to simulate a backfill
        NotableDomain.objects.all().delete()

        # User without links, to be ignored
        UserFactory().save()

        resource_count = backfill_task.backfill_domain_references(model_name='osf.OSFUser')
        # Just the test_user counted
        assert resource_count == 1
