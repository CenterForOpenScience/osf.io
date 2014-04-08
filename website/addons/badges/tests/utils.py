import string
import mock
import random

from website.addons.badges.model import Badge


def create_mock_badger(mock_badger):
    #mock_badger.configured = True
    mock_badger.name = 'Honey'
    mock_badger.email = 'Not@real.com'
    for _ in range(4):
        create_mock_badge(mock_badger)
    mock_badger.save()
    mock_badger.reload()
    return mock_badger


@mock.patch('website.addons.badges.model.badges.acquire_badge_image')
def create_mock_badge(issuer, mock_img, badge_data=None):
    mock_img.return_value = 'temp.png'
    if not badge_data:
        badge_data = create_badge_dict()
    return Badge.create(issuer, badge_data)


def create_badge_dict():
    return {
        'badgeName': ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(4)),
        'description': 'Just doesn\'t '.join(random.choice(string.ascii_letters + string.digits) for _ in range(6)),
        'imageurl': 'Image',
        'criteria': 'Don\'t give a '.join(random.choice(string.ascii_letters + string.digits) for _ in range(4))
    }


def get_garbage(length=10):
    return '<script><a><b><img>'.join(random.choice(string.ascii_letters + string.digits) for _ in range(length)).join('</script></b>')
