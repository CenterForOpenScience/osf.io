import pytest
from urllib.parse import urlparse

from osf_tests.factories import (
    CommentFactory,
    NodeFactory,
    PreprintFactory,
    RegistrationFactory,
)
from osf.models import (
    NotableDomain,
    DomainReference,
    SpamStatus
)
from osf.external.spam.tasks import check_resource_for_domains
from framework.celery_tasks.handlers import enqueue_task


@pytest.mark.django_db
class TestNotableDomain:

    @pytest.fixture()
    def node(self):
        return NodeFactory()

    @pytest.fixture()
    def spam_domain(self):
        return urlparse('http://I-am-a-domain.io/with-a-path/?and=&query=parms')

    @pytest.fixture()
    def marked_as_spam_domain(self):
        return NotableDomain.objects.create(
            domain='http://I-am-a-domain.io',
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT,
        )

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_moderate_domains(self, factory, spam_domain):
        obj = factory()
        assert obj.moderate_domains(content=spam_domain.geturl())
        domain = NotableDomain.objects.get(domain=f'{spam_domain.scheme}://{spam_domain.netloc.lower()}')
        assert domain.note == NotableDomain.Note.UNKNOWN
        assert DomainReference.objects.get().domain == domain
        assert DomainReference.objects.get().referrer == obj

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_add_domains_to_moderation_queue(self, factory, spam_domain):
        obj = factory()
        obj.add_domains_to_moderation_queue([spam_domain.geturl()])
        domain = NotableDomain.objects.get(
            note=NotableDomain.Note.UNKNOWN
        )
        assert domain.domain == f'{spam_domain.scheme}://{spam_domain.netloc.lower()}'
        assert DomainReference.objects.get().domain == domain
        assert DomainReference.objects.get().referrer == obj

    def test_has_spam_domain(self, spam_domain, marked_as_spam_domain):
        assert not NotableDomain.has_spam_domain('I-am-NOT-a-spam-domain')
        assert NotableDomain.has_spam_domain(spam_domain.geturl())

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_check_domain_confirm_spam(self, factory, spam_domain, marked_as_spam_domain):
        obj = factory()
        obj.moderate_domains(spam_domain.geturl(), confirm_spam=True)
        obj.reload()
        assert obj.spam_status == SpamStatus.SPAM

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_check_domain_task(self, factory, spam_domain, marked_as_spam_domain):
        obj = factory()
        enqueue_task(check_resource_for_domains.s(guid=obj.guids.first()._id, content=spam_domain.geturl()))
        obj.reload()
        NotableDomain.objects.get(domain=f'{spam_domain.scheme}://{spam_domain.netloc}')
        assert obj.spam_status == SpamStatus.SPAM
