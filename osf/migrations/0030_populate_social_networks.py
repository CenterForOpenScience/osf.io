# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from osf.models.user import SocialNetwork


SOCIAL_NETWORKS = [
    {
        '_id': 'twitter',
        'name': 'Twitter',
        'base_url': 'https://twitter.com/'
    },
    {
        '_id': 'facebook',
        'name': 'Facebook',
        'base_url': 'https://www.facebook.com/'
    },
    {
        '_id': 'instagram',
        'name': 'Instagram',
        'base_url': 'https://instagram.com/'
    },
    {
        '_id': 'linkedin',
        'name': 'LinkedIn',
        'base_url': 'https://www.linkedin.com/'
    },
    {
        '_id': 'youtube',
        'name': 'YouTube',
        'base_url': 'https://www.youtube.com/'
    }
]

def add_social_networks(*args):
    for network in SOCIAL_NETWORKS:
        SocialNetwork.objects.get_or_create(**network)

def remove_social_networks(*args):
    for network in SOCIAL_NETWORKS:
        SocialNetwork.objects.get(**network).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0029_auto_20170510_1028'),
    ]

    operations = [
        migrations.RunPython(add_social_networks, remove_social_networks)
    ]
