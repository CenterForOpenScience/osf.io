import mock
import pytest
from urllib.parse import urlparse

from osf_tests.factories import (
    CommentFactory,
    PreprintFactory,
    RegistrationFactory,
)
from osf.models import (
    NotableDomain,
    DomainReference,
    SpamStatus
)

from osf.external.spam.tasks import check_resource_for_domains
from osf_tests.factories import SessionFactory, NodeFactory
from framework.sessions import set_session
from osf.utils.workflows import DefaultStates
from django.contrib.contenttypes.models import ContentType

from website import settings


@pytest.mark.django_db
class TestNotableDomain:

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
    def test_check_resource_for_domains_moderation_queue(self, factory, spam_domain):
        obj = factory()
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=obj.guids.first()._id,
                content=spam_domain.geturl(),
            )
        )
        obj.reload()
        assert NotableDomain.objects.filter(
            domain=spam_domain.netloc,
            note=NotableDomain.Note.UNKNOWN
        ).count() == 1
        obj.reload()
        assert obj.spam_status == SpamStatus.UNKNOWN

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_check_resource_for_domains_spam(self, factory, spam_domain, marked_as_spam_domain):
        obj = factory()
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=obj.guids.first()._id,
                content=spam_domain.geturl(),
            )
        )
        obj.reload()
        assert NotableDomain.objects.filter(
            domain=spam_domain.netloc,
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        ).count() == 1
        obj.reload()
        assert obj.spam_status == SpamStatus.SPAM
        assert DomainReference.objects.filter(
            referrer_object_id=obj.id,
            referrer_content_type=ContentType.objects.get_for_model(obj),
            domain__domain=spam_domain.netloc
        ).count() == 1

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, RegistrationFactory, PreprintFactory])
    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    def test_spam_check(self, app, factory, spam_domain, marked_as_spam_domain, request_context):
        obj = factory()
        obj.is_public = True
        obj.is_published = True
        obj.machine_state = DefaultStates.PENDING.value
        obj.description = f'I\'m spam: {spam_domain.geturl()} me too: {spam_domain.geturl()}' \
                          f' iamNOTspam.org i-am-a-ham.io  https://stillNotspam.io'
        creator = getattr(obj, 'creator', None) or getattr(obj.node, 'creator')
        s = SessionFactory(user=creator)
        set_session(s)
        obj.save()
        assert NotableDomain.objects.filter(
            domain=spam_domain.netloc,
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        ).count() == 1
        assert NotableDomain.objects.filter(
            domain='iamNOTspam.org',
            note=NotableDomain.Note.UNKNOWN
        ).count() == 1
        assert DomainReference.objects.filter(
            referrer_object_id=obj.id,
            referrer_content_type=ContentType.objects.get_for_model(obj),
            domain__domain='iamNOTspam.org'
        ).count() == 1
        assert NotableDomain.objects.filter(
            domain='stillNotspam.io',
            note=NotableDomain.Note.UNKNOWN
        ).count() == 1
        assert DomainReference.objects.filter(
            referrer_object_id=obj.id,
            referrer_content_type=ContentType.objects.get_for_model(obj),
            domain__domain='stillNotspam.io'
        ).count() == 1
        obj.reload()
        assert obj.spam_status == SpamStatus.SPAM
