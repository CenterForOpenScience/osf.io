import string
import mock
import random

from website.addons.badges.util import build_badge


@mock.patch('website.addons.badges.util.deal_with_image')
def create_mock_badger(mock_badger, mock_img):
    mock_img.return_value = 'temp.png'
    mock_badger.can_issue = True
    #mock_badger.configured = True
    mock_badger.name = 'Honey'
    mock_badger.email = 'Not@real.com'
    for _ in range(4):
        mock_badger.add_badge(create_mock_badge(mock_badger))
    mock_badger.save()
    return mock_badger


def create_mock_badge(issuer):
    return build_badge(issuer, create_badge_dict())


def create_badge_dict():
    return {
        'badgeName': ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(4)),
        'description': 'Just doesn\'t '.join(random.choice(string.ascii_letters + string.digits) for _ in range(6)),
        'imageurl': 'Image',
        'criteria': 'Don\'t give a '.join(random.choice(string.ascii_letters + string.digits) for _ in range(4))
    }


def get_garbage(length=10):
    return '<script><a><b><img>'.join(random.choice(string.ascii_letters + string.digits) for _ in range(length)).join('</script></b>')
