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
from framework import sessions
from framework.flask import request
from osf_tests.factories import SessionFactory, UserFactory, NodeFactory
from framework.sessions import set_session
from osf.utils.workflows import DefaultStates
from framework.flask import add_handlers, app
from framework.celery_tasks import handlers as celery_task_handlers


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
    def test_check_resource_for_domains_moderation_queue(self, factory, spam_domain):
        obj = factory()
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=self.guids.first()._id,
                content=spam_domain.geturl(),
            )
        )
        obj.reload()
        NotableDomain.objects.get(
            domain=spam_domain.netloc,
            note=NotableDomain.Note.UNKNOWN
        )
        obj.reload()
        assert obj.spam_status == SpamStatus.UNKNOWN

    @pytest.mark.enable_enqueue_task
    @pytest.mark.parametrize('factory', [NodeFactory, CommentFactory, PreprintFactory, RegistrationFactory])
    def test_check_resource_for_domains_spam(self, factory, spam_domain, marked_as_spam_domain):
        obj = factory()
        check_resource_for_domains.apply_async(
            kwargs=dict(
                guid=self.guids.first()._id,
                content=spam_domain.geturl(),
            )
        )
        obj.reload()
        NotableDomain.objects.get(
            domain=spam_domain.netloc,
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        )
        obj.reload()
        assert obj.spam_status == SpamStatus.SPAM

    @pytest.mark.parametrize('factory', [NodeFactory, RegistrationFactory, PreprintFactory])
    def test_spam_check(self, app, factory, spam_domain, marked_as_spam_domain):
        with app.test_request_context(headers={
            'Remote-Addr': '146.9.219.56',
            'User-Agent': 'Mozilla/5.0 (X11; U; SunOS sun4u; en-US; rv:0.9.4.1) Gecko/20020518 Netscape6/6.2.3'
        }):
            obj = factory()

            setattr(obj, 'is_public', True)
            setattr(obj, 'is_published', True)
            setattr(obj, 'machine_state',  DefaultStates.PENDING.value)
            obj.description = f'I\'m spam: {spam_domain.geturl()} me too: {spam_domain.geturl()}  iamNOTspam.org  https://stillNotspam.io'
            creator = getattr(obj, 'creator', None) or getattr(obj.node, 'creator')
            s = SessionFactory(user=creator)
            set_session(s)
            obj.save()
            NotableDomain.objects.get(
                domain=spam_domain.netloc,
                note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
            )
            NotableDomain.objects.get(
                domain='iamNOTspam.org',
                note=NotableDomain.Note.UNKNOWN
            )
            NotableDomain.objects.get(
                domain='stillNotspam.io',
                note=NotableDomain.Note.UNKNOWN
            )
            obj.reload()
            assert obj.spam_status == SpamStatus.SPAM
