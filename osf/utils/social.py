from django.apps import apps

SOCIAL_NETWORKS = [
    {
        'name': 'Twitter',
        'base_url': 'https://twitter.com/'
    },
    {
        'name': 'Facebook',
        'base_url': 'https://www.facebook.com/'
    },
    {
        'name': 'Instagram',
        'base_url': 'https://instagram.com/'
    },
    {
        'name': 'LinkedIn',
        'base_url': 'https://www.linkedin.com/'
    },
    {
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
