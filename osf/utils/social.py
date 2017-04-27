from django.apps import apps

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

def ensure_social_networks():
    SocialNetwork = apps.get_model('osf.SocialNetwork')
    for network in SOCIAL_NETWORKS:
        try:
            SocialNetwork.objects.get(name=network['name'])
        except SocialNetwork.DoesNotExist:
            new_network = SocialNetwork(**network)
            new_network.save()
