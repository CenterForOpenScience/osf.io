"""Various node-related utilities."""
from django.apps import apps
from django.db.models import Q

from website import settings
# Alias the project serializer

def serialize_node(*args, **kwargs):
    from website.project.views.node import _view_project
    return _view_project(*args, **kwargs)  # Not recommended practice


def recent_public_registrations(n=10):
    Registration = apps.get_model('osf.Registration')

    return Registration.objects.filter(
        is_public=True,
        is_deleted=False,
    ).filter(
        Q(Q(embargo__isnull=True) | ~Q(embargo__state='unapproved')) &
        Q(Q(retraction__isnull=True) | ~Q(retraction__state='approved'))
    ).get_roots().order_by('-registered_date')[:n]


def activity():
    """Generate analytics for most popular public projects and registrations.
    Called by `scripts/update_populate_projects_and_registrations`
    """
    Node = apps.get_model('osf.AbstractNode')
    popular_public_projects = []
    popular_public_registrations = []
    # New and Noteworthy projects are updated manually
    new_and_noteworthy_projects = list(Node.objects.get(guids___id=settings.NEW_AND_NOTEWORTHY_LINKS_NODE, guids___id__isnull=False).nodes_pointer)
    return {
        'new_and_noteworthy_projects': new_and_noteworthy_projects,
        'recent_public_registrations': recent_public_registrations(),
        'popular_public_projects': popular_public_projects,
        'popular_public_registrations': popular_public_registrations
    }

# Credit to https://gist.github.com/cizixs/be41bbede49a772791c08491801c396f
def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1000.0:
            return f'{num:3.1f}{unit}{suffix}'
        num /= 1000.0
    return '{:.1f}{}{}'.format(num, 'Y', suffix)


def get_storage_limits_css(node):
    from osf.models import Node

    if not isinstance(node, Node):
        return None
    status = node.storage_limit_status

    if status is settings.StorageLimits.APPROACHING_PRIVATE and node.is_public:
        return None
    elif status is settings.StorageLimits.APPROACHING_PRIVATE:
        return {
            'text': 'approaching',
            'class': 'btn-warning storage-warning',
            'disableUploads': False,
            'canMakePrivate': True
        }
    elif status is settings.StorageLimits.OVER_PRIVATE and not node.is_public:
        return {
            'text': 'over',
            'class': 'btn-danger  storage-warning',
            'disableUploads': True,
            'canMakePrivate': False
        }
    elif status is settings.StorageLimits.OVER_PRIVATE and node.is_public:
        return {
            'text': None,
            'class': None,
            'disableUploads': False,
            'canMakePrivate': False
        }
    elif status is settings.StorageLimits.APPROACHING_PUBLIC:
        return {
            'text': 'approaching',
            'class': 'btn-warning  storage-warning',
            'disableUploads': False,
            'canMakePrivate': False

        }
    elif status is settings.StorageLimits.OVER_PUBLIC:
        return {
            'text': 'over',
            'class': 'btn-danger  storage-warning',
            'disableUploads': True,
            'canMakePrivate': False
        }
    elif status is settings.StorageLimits.DEFAULT:
        return None
    elif status is settings.StorageLimits.NOT_CALCULATED:
        return None
    else:
        raise NotImplementedError()
