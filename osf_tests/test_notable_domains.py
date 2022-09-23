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
        return urlparse('http://i-am-a-domain.io/with-a-path/?and=&query=parms')

    @pytest.fixture()
    def marked_as_spam_domain(self):
        return NotableDomain.objects.create(
            domain='i-am-a-domain.io',
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT,
        )

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_add_domains_to_moderation_queue(self, factory, spam_domain):
        obj = factory()
        enqueue_task(check_resource_for_domains.s(guid=obj.guids.first()._id, content=spam_domain.geturl()))
        obj.reload()
        NotableDomain.objects.get(
            domain=spam_domain.netloc,
            note=NotableDomain.Note.UNKNOWN
        )
        obj.reload()
        assert obj.spam_status == SpamStatus.UNKNOWN

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_check_domain_task(self, factory, spam_domain, marked_as_spam_domain):
        obj = factory()
        enqueue_task(check_resource_for_domains.s(guid=obj.guids.first()._id, content=spam_domain.geturl()))
        obj.reload()
        NotableDomain.objects.get(
            domain=spam_domain.netloc,
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        )
        obj.reload()
        assert obj.spam_status == SpamStatus.SPAM
