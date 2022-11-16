import mock
import pytest
from types import SimpleNamespace

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

from osf.external.spam import tasks as spam_tasks
from osf_tests.factories import SessionFactory, NodeFactory
from framework.sessions import set_session
from osf.utils.workflows import DefaultStates
from django.contrib.contenttypes.models import ContentType

from website import settings


class TestDomainExtraction:

    @pytest.mark.parametrize('protocol_component', ['', 'http://', 'https://', 'ftp://'])
    @pytest.mark.parametrize('www_component', ['', 'www.'])
    def test_extract_domains__optional_components(self, protocol_component, www_component):
        test_url = f'{protocol_component}{www_component}osf.io'
        sample_text = f'This is a link: {test_url}'
        with mock.patch.object(spam_tasks.requests, 'head'):
            domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == ['osf.io']

    def test_extract_domains__url_in_quotes(self):
        sample_text = '"osf.io"'
        with mock.patch.object(spam_tasks.requests, 'head'):
            domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == ['osf.io']

    def test_extract_domains__url_in_parens(self):
        sample_text = '(osf.io)'
        with mock.patch.object(spam_tasks.requests, 'head'):
            domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == ['osf.io']

    def test_extract_domains__captures_domain_with_multiple_subdomains(self):
        sample_text = 'This is a link: https://api.test.osf.io'
        with mock.patch.object(spam_tasks.requests, 'head'):
            domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == ['api.test.osf.io']

    def test_extract_domains__captures_multiple_domains(self):
        sample_text = 'This is a domain: http://osf.io. This is another domain: www.cos.io'
        with mock.patch.object(spam_tasks.requests, 'head'):
            domains = set(spam_tasks._extract_domains(sample_text))
        assert domains == {'osf.io', 'cos.io'}

    def test_extract_domains__no_domains(self):
        sample_text = 'http://fakeout!'
        with mock.patch.object(spam_tasks.requests, 'head') as mock_head:
            domains = set(spam_tasks._extract_domains(sample_text))
        assert not domains
        mock_head.assert_not_called()

    def test_extract_domains__false_positive(self):
        sample_text = 'This.will.not.connect'
        with mock.patch.object(spam_tasks.requests, 'head') as mock_head:
            mock_head.side_effect = spam_tasks.requests.exceptions.ConnectionError
            domains = set(spam_tasks._extract_domains(sample_text))
        assert not domains
        mock_head.assert_called()

    def test_extract_domains__follows_redirect(self):
        mock_response = SimpleNamespace()
        mock_response.status_code = 302
        mock_response.headers = {'location': 'redirected.com'}
        sample_text = 'redirect.me'
        with mock.patch.object(spam_tasks.requests, 'head', return_value=mock_response):
            domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == ['redirected.com']

    def test_extract_domains__deduplicates(self):
        sample_text = 'osf.io osf.io osf.io and, oh, yeah, osf.io'
        with mock.patch.object(spam_tasks.requests, 'head'):
            domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == ['osf.io']

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
    def test_check_resource_for_domains_moderation_queue(self, spam_domain, factory):
        obj = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
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
    def test_check_resource_for_domains_spam(self, spam_domain, marked_as_spam_domain, factory):
        obj = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
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
        with mock.patch.object(spam_tasks.requests, 'head'):
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

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_check_resource_for_duplicate_spam_domains(self, factory, spam_domain, marked_as_spam_domain):
        obj = factory()
        obj.spam_data['domains'] = [spam_domain.netloc]
        obj.save()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj.guids.first()._id,
                    content=f'{spam_domain.geturl()}',
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

@pytest.mark.django_db
@pytest.mark.enable_enqueue_task
class TestNotableDomainReclassification:
    spam_domain_one = urlparse('http://spammy-domain.io')
    spam_domain_two = urlparse('http://prosciutto-crudo.io')
    unknown_domain = urlparse('https://unknown-domain.io')
    ignored_domain = urlparse('https://cos.io')

    @pytest.fixture()
    def spam_notable_domain_one(self):
        return NotableDomain.objects.create(
            domain=self.spam_domain_one.netloc,
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT,
        )

    @pytest.fixture()
    def spam_notable_domain_two(self):
        return NotableDomain.objects.create(
            domain=self.spam_domain_two.netloc,
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT,
        )

    @pytest.fixture()
    def unknown_notable_domain(self):
        return NotableDomain.objects.create(
            domain=self.unknown_domain.netloc,
            note=NotableDomain.Note.UNKNOWN,
        )

    @pytest.fixture()
    def ignored_notable_domain(self):
        return NotableDomain.objects.create(
            domain=self.ignored_domain.netloc,
            note=NotableDomain.Note.IGNORED,
        )

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_spam_to_unknown_one_spam_domain(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj_one.guids.first()._id,
                    content=f'{self.spam_domain_one.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
                )
            )

        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == set([self.spam_domain_one.netloc])
        spam_notable_domain_one.note = NotableDomain.Note.UNKNOWN
        spam_notable_domain_one.save()
        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert len(obj_one.spam_data['domains']) == 0

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_spam_to_unknown_two_spam_domains(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_two = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj_two.guids.first()._id,
                    content=f'{self.spam_domain_one.geturl()} {self.spam_domain_two.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
                )
            )

        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == set([self.spam_domain_one.netloc, self.spam_domain_two.netloc])
        spam_notable_domain_one.note = NotableDomain.Note.UNKNOWN
        spam_notable_domain_one.save()
        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == set([self.spam_domain_two.netloc])

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_spam_to_unknown_marked_by_external(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_three = factory()
        obj_three.spam_data['who_flagged'] = 'some external spam checker'
        obj_three.save()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj_three.guids.first()._id,
                    content=f'{self.spam_domain_one.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
                )
            )

        obj_three.reload()
        assert obj_three.spam_status == SpamStatus.SPAM
        assert set(obj_three.spam_data['domains']) == set([self.spam_domain_one.netloc])
        spam_notable_domain_one.note = NotableDomain.Note.UNKNOWN
        spam_notable_domain_one.save()
        obj_three.reload()
        assert obj_three.spam_status == SpamStatus.SPAM
        assert len(obj_three.spam_data['domains']) == 0

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_spam_to_ignored_one_spam_domain(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj_one.guids.first()._id,
                    content=f'{self.spam_domain_one.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
                )
            )

        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == set([self.spam_domain_one.netloc])
        spam_notable_domain_one.note = NotableDomain.Note.IGNORED
        spam_notable_domain_one.save()
        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert len(obj_one.spam_data['domains']) == 0

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_spam_to_ignored_two_spam_domains(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_two = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj_two.guids.first()._id,
                    content=f'{self.spam_domain_one.geturl()} {self.spam_domain_two.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
                )
            )

        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == set([self.spam_domain_one.netloc, self.spam_domain_two.netloc])
        spam_notable_domain_one.note = NotableDomain.Note.IGNORED
        spam_notable_domain_one.save()
        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == set([self.spam_domain_two.netloc])

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_spam_to_ignored_makred_by_external(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_three = factory()
        obj_three.spam_data['who_flagged'] = 'some external spam checker'
        obj_three.save()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj_three.guids.first()._id,
                    content=f'{self.spam_domain_one.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
                )
            )

        obj_three.reload()
        assert obj_three.spam_status == SpamStatus.SPAM
        assert set(obj_three.spam_data['domains']) == set([self.spam_domain_one.netloc])
        spam_notable_domain_one.note = NotableDomain.Note.IGNORED
        spam_notable_domain_one.save()
        obj_three.reload()
        assert obj_three.spam_status == SpamStatus.SPAM
        assert len(obj_three.spam_data['domains']) == 0

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_unknown_to_spam_unknown_plus_ignored(self, factory, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj_one.guids.first()._id,
                    content=f'{self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
                )
            )

        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert 'domains' not in obj_one.spam_data
        unknown_notable_domain.note = NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        unknown_notable_domain.save()
        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == set([self.unknown_domain.netloc])

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_unknown_to_spam_unknown_only(self, factory, unknown_notable_domain, ignored_notable_domain):
        obj_two = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj_two.guids.first()._id,
                    content=f'{self.unknown_domain.geturl()}',
                )
            )

        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.UNKNOWN
        assert 'domains' not in obj_two.spam_data
        unknown_notable_domain.note = NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        unknown_notable_domain.save()
        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == set([self.unknown_domain.netloc])

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_ignored_to_spam_unknown_plus_ignored(self, factory, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj_one.guids.first()._id,
                    content=f'{self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
                )
            )

        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert 'domains' not in obj_one.spam_data
        ignored_notable_domain.note = NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        ignored_notable_domain.save()
        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == set([self.ignored_domain.netloc])

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_from_ignored_to_spam_ignored_only(self, factory, unknown_notable_domain, ignored_notable_domain):
        obj_two = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=obj_two.guids.first()._id,
                    content=f'{self.ignored_domain.geturl()}',
                )
            )

        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.UNKNOWN
        assert 'domains' not in obj_two.spam_data
        ignored_notable_domain.note = NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        ignored_notable_domain.save()
        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == set([self.ignored_domain.netloc])
