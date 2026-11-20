import pytest

from admin.nodes.templatetags.node_extras import get_spam_status
from osf.models import NotableDomain
from osf_tests.factories import UserFactory


@pytest.mark.django_db
def test_spam_status_shown_for_spam_user_with_trusted_domain():
    NotableDomain.objects.create(domain='trusted.edu', note=NotableDomain.Note.ASSUME_HAM_UNTIL_REPORTED)
    user = UserFactory()
    user.emails.create(address='x@trusted.edu')
    assert 'assumed Ham' in get_spam_status(user)
    user.confirm_spam(save=True, force=True, notify=False)
    assert 'Spam' in get_spam_status(user)
    assert 'assumed Ham' not in get_spam_status(user)
