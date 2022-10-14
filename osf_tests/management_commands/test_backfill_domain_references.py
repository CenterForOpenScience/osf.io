import pytest
import datetime
from django.contrib.contenttypes.models import ContentType

from addons.wiki.tests.factories import WikiVersionFactory
from osf.management.commands.backfill_domain_references import backfill_domain_references
from osf_tests.factories import (
    NodeFactory,
    RegistrationFactory,
    CommentFactory,
    PreprintFactory
)
from osf.models.notable_domain import DomainReference, NotableDomain
from urllib.parse import urlparse


@pytest.mark.django_db
class TestBackfillDomainReferences:

    @pytest.fixture()
    def node(self):
        return NodeFactory()

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture()
    def spam_domain(self):
        return urlparse('http://I-am-a-domain.io/with-a-path/?and=&query=parms')

    @pytest.fixture()
    def node_with_domain(self, spam_domain):
        return NodeFactory(description=f'I am spam: {spam_domain.geturl()}', is_public=True)

    @pytest.fixture()
    def registration_with_domain(self, spam_domain):
        return RegistrationFactory(description=f'I am spam: {spam_domain.geturl()}', is_public=True)

    @pytest.fixture()
    def comment_with_domain(self, spam_domain):
        return CommentFactory(content=f'I am spam: {spam_domain.geturl()}')

    @pytest.fixture()
    def preprint_with_domain(self, spam_domain):
        return PreprintFactory(description=f'I am spam: {spam_domain.geturl()}')

    @pytest.fixture()
    def wiki_with_domain(self, spam_domain):
        return WikiVersionFactory(content=f'I am spam: {spam_domain.geturl()}')

    @pytest.mark.enable_enqueue_task
    def test_backfill_domain_references(self,
                                        node_with_domain,
                                        registration_with_domain,
                                        comment_with_domain,
                                        preprint_with_domain,
                                        wiki_with_domain,
                                        spam_domain):

        # Node
        backfill_domain_references(model_name='osf.Node', date_modified=datetime.datetime.now())
        domain = NotableDomain.objects.get(domain=spam_domain.netloc.lower())
        assert DomainReference.objects.get(
            referrer_object_id=node_with_domain.id,
            referrer_content_type=ContentType.objects.get_for_model(node_with_domain),
        ).domain == domain

        # Registration
        backfill_domain_references(model_name='osf.Registration', date_modified=datetime.datetime.now())
        assert DomainReference.objects.get(
            referrer_object_id=registration_with_domain.id,
            referrer_content_type=ContentType.objects.get_for_model(registration_with_domain),
        ).domain == domain
        # Registration's registered_from node
        assert DomainReference.objects.get(
            referrer_object_id=registration_with_domain.registered_from.id,
            referrer_content_type=ContentType.objects.get_for_model(registration_with_domain.registered_from),
        ).domain == domain

        # Comment
        backfill_domain_references(model_name='osf.Comment', date_modified=datetime.datetime.now())
        assert DomainReference.objects.get(
            referrer_content_type=ContentType.objects.get_for_model(comment_with_domain),
        ).domain == domain

        backfill_domain_references(model_name='addons_wiki.WikiVersion', date_modified=datetime.datetime.now())
        # WikiVersion (these have no spam status so point to the user)
        assert DomainReference.objects.get(
            referrer_object_id=wiki_with_domain.wiki_page.node.id,
            referrer_content_type=ContentType.objects.get_for_model(wiki_with_domain.wiki_page.node),
        ).domain == domain
