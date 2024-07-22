from unittest import mock
import pytest
from django.contrib.contenttypes.models import ContentType
from types import SimpleNamespace
from urllib.parse import urlparse

from flask import g

from addons.wiki.tests.factories import WikiVersionFactory
from osf.external.spam import tasks as spam_tasks
from osf.models import (
    NotableDomain,
    DomainReference,
    SpamStatus
)
from osf.utils.workflows import DefaultStates
from osf_tests.factories import (
    CommentFactory,
    NodeFactory,
    PreprintFactory,
    RegistrationFactory,
    UserFactory
)


class TestDomainExtraction:

    @pytest.mark.parametrize('protocol_component', ['', 'http://', 'https://', 'ftp://'])
    @pytest.mark.parametrize('www_component', ['', 'www.'])
    def test_extract_domains__optional_components(self, protocol_component, www_component, mock_spam_head_request):
        test_url = f'{protocol_component}{www_component}osf.io'
        sample_text = f'This is a link: {test_url}'
        domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == [('osf.io', NotableDomain.Note.UNKNOWN)]

    def test_extract_domains__url_in_quotes(self, mock_spam_head_request):
        sample_text = '"osf.io"'
        domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == [('osf.io', NotableDomain.Note.UNKNOWN)]

    def test_extract_domains__url_in_parens(self, mock_spam_head_request):
        sample_text = '(osf.io)'
        domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == [('osf.io', NotableDomain.Note.UNKNOWN)]

    def test_extract_domains__captures_domain_with_multiple_subdomains(self, mock_spam_head_request):
        sample_text = 'This is a link: https://api.test.osf.io'
        domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == [('api.test.osf.io', NotableDomain.Note.UNKNOWN)]

    def test_extract_domains__captures_multiple_domains(self, mock_spam_head_request):
        sample_text = 'This is a domain: http://osf.io. This is another domain: www.cos.io'
        domains = set(spam_tasks._extract_domains(sample_text))
        assert domains == {
            ('osf.io', NotableDomain.Note.UNKNOWN),
            ('cos.io', NotableDomain.Note.UNKNOWN),
        }

    def test_extract_domains__no_domains(self, mock_spam_head_request):
        sample_text = 'http://fakeout!'
        domains = set(spam_tasks._extract_domains(sample_text))
        assert not domains

    def test_extract_domains__unverfied_if_does_not_resolve(self, mock_spam_head_request):
        mock_spam_head_request.side_effect = spam_tasks.requests.exceptions.ConnectionError
        sample_text = 'This.will.not.connect'

        domains = set(spam_tasks._extract_domains(sample_text))
        assert domains == {('This.will.not.connect', NotableDomain.Note.UNVERIFIED)}

    def test_actract_domains__returned_on_error(self, mock_spam_head_request):
        sample_text = 'This.will.timeout'
        mock_spam_head_request.side_effect = spam_tasks.requests.exceptions.Timeout
        domains = set(spam_tasks._extract_domains(sample_text))
        assert domains == {(sample_text, NotableDomain.Note.UNVERIFIED)}

    @pytest.mark.parametrize('status_code', [301, 302, 303, 307, 308])
    def test_extract_domains__follows_redirect(self, status_code, mock_spam_head_request):
        mock_response = SimpleNamespace()
        mock_response.status_code = status_code
        mock_response.headers = {'location': 'redirected.com'}
        mock_spam_head_request.return_value = mock_response
        domains = list(spam_tasks._extract_domains('redirect.me'))
        assert domains == [('redirected.com', NotableDomain.Note.UNKNOWN)]

    def test_extract_domains__redirect_code_no_location(self, mock_spam_head_request):
        mock_response = SimpleNamespace()
        mock_response.status_code = 301
        mock_response.headers = {}
        sample_text = 'redirect.me'
        mock_spam_head_request.return_value = mock_response
        domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == [('redirect.me', NotableDomain.Note.UNKNOWN)]

    def test_extract_domains__redirect_code_bad_location(self, mock_spam_head_request):
        mock_response = SimpleNamespace()
        mock_response.status_code = 301
        mock_response.headers = {'location': 'haha'}
        mock_spam_head_request.return_value = mock_response
        sample_text = 'redirect.me'
        domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == [('redirect.me', NotableDomain.Note.UNKNOWN)]

    def test_extract_domains__redirect_with_full_url_no_protocol(self, mock_spam_head_request):
        mock_response = SimpleNamespace()
        mock_response.status_code = 301
        mock_response.headers = {'location': 'osf.io'}
        target_url = 'redirect.me/this-is-a-path/another-level-path/index.php'
        sample_text = target_url
        mock_spam_head_request.return_value = mock_response
        domains = list(spam_tasks._extract_domains(sample_text))
        mock_spam_head_request.assert_called_once_with(f'https://{target_url}', timeout=60)
        assert domains == [('osf.io', NotableDomain.Note.UNKNOWN)]

    def test_extract_domains__redirect_with_full_url_and_protocol(self, mock_spam_head_request):
        mock_response = SimpleNamespace()
        mock_response.status_code = 301
        mock_response.headers = {'location': 'osf.io'}
        target_url = 'ftp://redirect.me/this-is-a-path/another-level-path/index.php'
        sample_text = target_url
        mock_spam_head_request.return_value = mock_response
        domains = list(spam_tasks._extract_domains(sample_text))
        mock_spam_head_request.assert_called_once_with(target_url, timeout=60)
        assert domains == [('osf.io', NotableDomain.Note.UNKNOWN)]

    def test_extract_domains__deduplicates(self, mock_spam_head_request):
        sample_text = 'osf.io osf.io osf.io and, oh, yeah, osf.io'
        domains = list(spam_tasks._extract_domains(sample_text))
        assert domains == [('osf.io', NotableDomain.Note.UNKNOWN)]

    def test_extract_domains__ignores_floats(self, mock_spam_head_request):
        sample_text = 'this is a number 3.1415 not a domain'
        domains = list(spam_tasks._extract_domains(sample_text))
        assert not domains


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

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_check_resource_for_domains_moderation_queue(self, spam_domain, factory):
        obj = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj.guids.first()._id,
                content=spam_domain.geturl(),
            )

        obj.reload()
        assert NotableDomain.objects.filter(
            domain=spam_domain.netloc,
            note=NotableDomain.Note.UNKNOWN
        ).count() == 1
        obj.reload()
        assert obj.spam_status == SpamStatus.UNKNOWN

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_check_resource_for_domains_spam(self, spam_domain, marked_as_spam_domain, factory):
        obj = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj.guids.first()._id,
                content=spam_domain.geturl(),
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
    def test_spam_check(self, app, factory, spam_domain, marked_as_spam_domain, request_context):
        obj = factory()
        obj.is_public = True
        obj.is_published = True
        obj.machine_state = DefaultStates.PENDING.value
        obj.description = f'I\'m spam: {spam_domain.geturl()} me too: {spam_domain.geturl()}' \
                          f' iamNOTspam.org i-am-a-ham.io  https://stillNotspam.io'
        creator = getattr(obj, 'creator', None) or getattr(obj.node, 'creator')
        with mock.patch.object(spam_tasks.requests, 'head'):
            g.current_session = {'auth_user_id': creator._id}
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

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_check_resource_for_duplicate_spam_domains(self, factory, spam_domain, marked_as_spam_domain):
        obj = factory()
        obj.spam_data['domains'] = [spam_domain.netloc]
        obj.save()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj.guids.first()._id,
                content=f'{spam_domain.geturl()}',
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
    def test_extract_domains_from_wiki__public_project_extracts_domains_on_wiki_save(self, request_context):
        assert DomainReference.objects.count() == 0

        wiki_version = WikiVersionFactory()
        project = wiki_version.wiki_page.node
        project.is_public = True
        project.save()
        wiki_version.content = '[EXTREME VIDEO] <b><a href="https://cos.io/JAkeEloit">WATCH VIDEO</a></b>'

        g.current_session = {'auth_user_id': project.creator._id}
        with mock.patch.object(spam_tasks.requests, 'head'):
            wiki_version.save()

        references = DomainReference.objects.filter(domain__domain='cos.io')
        assert references.count() == 1
        assert references.first().referrer == project

    @pytest.mark.enable_enqueue_task
    def test_extract_domains_from_wiki__project_checks_wiki_content_on_make_public(self, request_context):
        wiki_version = WikiVersionFactory()
        project = wiki_version.wiki_page.node
        wiki_version.content = 'This has a domain: https://cos.io'
        wiki_version.save()

        assert DomainReference.objects.count() == 0
        g.current_session = {'auth_user_id': project.creator._id}
        with mock.patch.object(spam_tasks.requests, 'head'):
            project.set_privacy(permissions='public')

        references = DomainReference.objects.filter(domain__domain='cos.io')
        assert references.count() == 1
        assert references.first().referrer == project

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

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory, UserFactory])
    def test_from_spam_to_unknown_one_spam_domain(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj_one.guids.first()._id,
                content=f'{self.spam_domain_one.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
            )

        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == {self.spam_domain_one.netloc}
        spam_notable_domain_one.note = NotableDomain.Note.UNKNOWN
        spam_notable_domain_one.save()
        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert len(obj_one.spam_data['domains']) == 0

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory, UserFactory])
    def test_from_spam_to_unknown_two_spam_domains(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_two = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj_two.guids.first()._id,
                content=f'{self.spam_domain_one.geturl()} {self.spam_domain_two.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
            )

        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == {self.spam_domain_one.netloc, self.spam_domain_two.netloc}
        spam_notable_domain_one.note = NotableDomain.Note.UNKNOWN
        spam_notable_domain_one.save()
        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == {self.spam_domain_two.netloc}

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory, UserFactory])
    def test_from_spam_to_unknown_marked_by_external(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_three = factory()
        obj_three.spam_data['who_flagged'] = 'some external spam checker'
        obj_three.save()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj_three.guids.first()._id,
                content=f'{self.spam_domain_one.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
            )

        obj_three.reload()
        assert obj_three.spam_status == SpamStatus.SPAM
        assert set(obj_three.spam_data['domains']) == {self.spam_domain_one.netloc}
        spam_notable_domain_one.note = NotableDomain.Note.UNKNOWN
        spam_notable_domain_one.save()
        obj_three.reload()
        assert obj_three.spam_status == SpamStatus.SPAM
        assert len(obj_three.spam_data['domains']) == 0

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory, UserFactory])
    def test_from_spam_to_ignored_one_spam_domain(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj_one.guids.first()._id,
                content=f'{self.spam_domain_one.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
            )

        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == {self.spam_domain_one.netloc}
        spam_notable_domain_one.note = NotableDomain.Note.IGNORED
        spam_notable_domain_one.save()
        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert len(obj_one.spam_data['domains']) == 0

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory, UserFactory])
    def test_from_spam_to_ignored_two_spam_domains(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_two = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj_two.guids.first()._id,
                content=f'{self.spam_domain_one.geturl()} {self.spam_domain_two.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
            )

        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == {self.spam_domain_one.netloc, self.spam_domain_two.netloc}
        spam_notable_domain_one.note = NotableDomain.Note.IGNORED
        spam_notable_domain_one.save()
        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == {self.spam_domain_two.netloc}

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory, UserFactory])
    def test_from_spam_to_ignored_makred_by_external(self, factory, spam_notable_domain_one, spam_notable_domain_two, unknown_notable_domain, ignored_notable_domain):
        obj_three = factory()
        obj_three.spam_data['who_flagged'] = 'some external spam checker'
        obj_three.save()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj_three.guids.first()._id,
                content=f'{self.spam_domain_one.geturl()} {self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
            )

        obj_three.reload()
        assert obj_three.spam_status == SpamStatus.SPAM
        assert set(obj_three.spam_data['domains']) == {self.spam_domain_one.netloc}
        spam_notable_domain_one.note = NotableDomain.Note.IGNORED
        spam_notable_domain_one.save()
        obj_three.reload()
        assert obj_three.spam_status == SpamStatus.SPAM
        assert len(obj_three.spam_data['domains']) == 0

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory, UserFactory])
    def test_from_unknown_to_spam_unknown_plus_ignored(self, factory, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj_one.guids.first()._id,
                content=f'{self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
            )

        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert 'domains' not in obj_one.spam_data
        unknown_notable_domain.note = NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        unknown_notable_domain.save()
        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == {self.unknown_domain.netloc}

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory, UserFactory])
    def test_from_unknown_to_spam_unknown_only(self, factory, unknown_notable_domain, ignored_notable_domain):
        obj_two = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj_two.guids.first()._id,
                content=f'{self.unknown_domain.geturl()}',
            )

        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.UNKNOWN
        assert 'domains' not in obj_two.spam_data
        unknown_notable_domain.note = NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        unknown_notable_domain.save()
        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == {self.unknown_domain.netloc}

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory, UserFactory])
    def test_from_ignored_to_spam_unknown_plus_ignored(self, factory, unknown_notable_domain, ignored_notable_domain):
        obj_one = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj_one.guids.first()._id,
                content=f'{self.unknown_domain.geturl()} {self.ignored_domain.geturl()}',
            )

        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.UNKNOWN
        assert 'domains' not in obj_one.spam_data
        ignored_notable_domain.note = NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        ignored_notable_domain.save()
        obj_one.reload()
        assert obj_one.spam_status == SpamStatus.SPAM
        assert set(obj_one.spam_data['domains']) == {self.ignored_domain.netloc}

    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory, UserFactory])
    def test_from_ignored_to_spam_ignored_only(self, factory, unknown_notable_domain, ignored_notable_domain):
        obj_two = factory()
        with mock.patch.object(spam_tasks.requests, 'head'):
            spam_tasks._check_resource_for_domains(
                guid=obj_two.guids.first()._id,
                content=f'{self.ignored_domain.geturl()}',
            )

        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.UNKNOWN
        assert 'domains' not in obj_two.spam_data
        ignored_notable_domain.note = NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        ignored_notable_domain.save()
        obj_two.reload()
        assert obj_two.spam_status == SpamStatus.SPAM
        assert set(obj_two.spam_data['domains']) == {self.ignored_domain.netloc}
