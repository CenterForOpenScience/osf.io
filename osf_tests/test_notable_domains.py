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
        assert obj.spam_data['domains'] == [spam_domain.netloc]
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

class TestNotableDomainReclassification:
    @pytest.fixture()
    def spam_domain_one(self):
        return urlparse('http://spammy-domain.io')

    @pytest.fixture()
    def spam_domain_two(self):
        return urlparse('http://prosciutto-crudo.io')

    @pytest.fixture()
    def unknown_domain(self):
        return urlparse('https://uknown-domain.io')

    @pytest.fixture()
    def ignored_domain(self):
        return urlparse('https://cos.io')

    @pytest.fixture()
    def spam_notable_domain_one(self, spam_domain_one):
        return NotableDomain.objects.create(
            domain=spam_domain_one.netloc,
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT,
        )

    @pytest.fixture()
    def spam_notable_domain_two(self, spam_domain_two):
        return NotableDomain.objects.create(
            domain=spam_domain_two.netloc,
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT,
        )

    @pytest.fixture()
    def unknown_notable_domain(self, unknown_domain):
        return NotableDomain.objects.create(
            domain=unknown_domain.netloc,
            note=NotableDomain.Note.UNKNOWN,
        )

    @pytest.fixture()
    def ignored_notable_domain(self, ignored_domain):
        return NotableDomain.objects.create(
            domain=ignored_domain.netloc,
            note=NotableDomain.Note.IGNORED,
        )

    @pytest.mark.django_db
    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_spam_to_unknown(self, factory, spam_domain_one, spam_domain_two, unknown_domain, ignored_domain, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        obj_two = factory()
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=obj_one.guids.first()._id,
                content=f'{spam_domain_one.geturl()} {unknown_domain.geturl()} {ignored_domain.geturl()}',
            )
        )
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=obj_two.guids.first()._id,
                content=f'{spam_domain_one.geturl()} {spam_domain_two.geturl()} {unknown_domain.geturl()} {ignored_domain.geturl()}',
            )
        )
        obj_one.reload()
        obj_two.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == set([spam_domain_one.netloc])
        assert set(obj_two.spam_data['domains']) == set([spam_domain_one.netloc, spam_domain_two.netloc])
        spam_notable_domain_one.note = NotableDomain.Note.UNKNOWN
        spam_notable_domain_one.save()
        obj_one.reload()
        obj_two.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert obj_two.spam_status == SpamStatus.SPAM
        assert len(obj_one.spam_data['domains']) == 0
        assert set(obj_two.spam_data['domains']) == set([spam_domain_two.netloc])

    @pytest.mark.django_db
    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_spam_to_ignored(self, factory, spam_domain_one, spam_domain_two, unknown_domain, ignored_domain, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        obj_two = factory()
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=obj_one.guids.first()._id,
                content=f'{spam_domain_one.geturl()} {unknown_domain.geturl()} {ignored_domain.geturl()}',
            )
        )
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=obj_two.guids.first()._id,
                content=f'{spam_domain_one.geturl()} {spam_domain_two.geturl()} {unknown_domain.geturl()} {ignored_domain.geturl()}',
            )
        )
        obj_one.reload()
        obj_two.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == set([spam_domain_one.netloc])
        assert set(obj_two.spam_data['domains']) == set([spam_domain_one.netloc, spam_domain_two.netloc])
        spam_notable_domain_one.note = NotableDomain.Note.IGNORED
        spam_notable_domain_one.save()
        obj_one.reload()
        obj_two.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert obj_two.spam_status == SpamStatus.SPAM
        assert len(obj_one.spam_data['domains']) == 0
        assert set(obj_two.spam_data['domains']) == set([spam_domain_two.netloc])

    @pytest.mark.django_db
    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_unknown_to_spam(self, factory, unknown_domain, ignored_domain, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        obj_two = factory()
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=obj_one.guids.first()._id,
                content=f'{unknown_domain.geturl()} {ignored_domain.geturl()}',
            )
        )
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=obj_two.guids.first()._id,
                content=f'{unknown_domain.geturl()}',
            )
        )
        obj_one.reload()
        obj_two.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert obj_two.spam_status == SpamStatus.UNKNOWN
        assert 'domains' not in obj_one.spam_data
        assert 'domains' not in obj_two.spam_data
        unknown_notable_domain.note = NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        unknown_notable_domain.save()
        obj_one.reload()
        obj_two.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == set([unknown_domain.netloc])
        assert set(obj_two.spam_data['domains']) == set([unknown_domain.netloc])

    @pytest.mark.django_db
    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_ignored_to_spam(self, factory, unknown_domain, ignored_domain, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        obj_two = factory()
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=obj_one.guids.first()._id,
                content=f'{unknown_domain.geturl()} {ignored_domain.geturl()}',
            )
        )
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=obj_two.guids.first()._id,
                content=f'{ignored_domain.geturl()}',
            )
        )
        obj_one.reload()
        obj_two.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert obj_two.spam_status == SpamStatus.UNKNOWN
        assert 'domains' not in obj_one.spam_data
        assert 'domains' not in obj_two.spam_data
        ignored_notable_domain.note = NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        ignored_notable_domain.save()
        obj_one.reload()
        obj_two.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == set([ignored_domain.netloc])
        assert set(obj_two.spam_data['domains']) == set([ignored_domain.netloc])
