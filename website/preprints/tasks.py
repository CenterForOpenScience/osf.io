import datetime
import logging
import urlparse

import requests

from framework.celery_tasks import app as celery_app

from website import settings

logger = logging.getLogger(__name__)

@celery_app.task(ignore_results=True)
def on_preprint_updated(preprint_id):
    # WARNING: Only perform Read-Only operations in an asynchronous task, until Repeatable Read/Serializable
    # transactions are implemented in View and Task application layers.
    from website.models import PreprintService
    preprint = PreprintService.load(preprint_id)

    if settings.SHARE_URL and settings.SHARE_API_TOKEN:
        resp = requests.post('{}api/v2/normalizeddata/'.format(settings.SHARE_URL), json={
            'created_at': datetime.datetime.utcnow().isoformat(),
            'normalized_data': {
                '@graph': format_preprint(preprint)
            },
        }, headers={'Authorization': 'Bearer {}'.format(settings.SHARE_API_TOKEN)})
        logger.debug(resp.content)
        resp.raise_for_status()

def format_institution(institution):
    return [{
        '@id': '_:{}'.format(institution._id),
        '@type': 'institution',
        'name': institution.title,
    }]


def format_user(user):
    return sum([[{
        '@id': '_:{}'.format(user._id),
        '@type': 'person',
        'suffix': user.suffix,
        'given_name': user.given_name,
        'family_name': user.family_name,
        'additional_name': user.middle_names,
    }, {
        '@id': '_:throughidentifier-{}'.format(user._id),
        '@type': 'throughidentifiers',
        'person': {
            '@id': '_:{}'.format(user._id),
            '@type': 'person',
        },
        'identifier': {
            '@id': '_:identifier-{}'.format(user._id),
            '@type': 'identifier',
        }
    }, {
        '@id': '_:identifier-{}'.format(user._id),
        '@type': 'identifier',
        'url': urlparse.urljoin(settings.DOMAIN, user.profile_url),
        'base_url': settings.DOMAIN
    }]] + [[{
        '@id': '_:{}-{}'.format(user._id, institution._id),
        '@type': 'affiliation',
        'entity': {
            '@id': '_:{}'.format(institution._id),
            '@type': 'institution',
        },
        'person': {
            '@id': '_:{}'.format(user._id),
            '@type': 'person',
        }
    }] + format_institution(institution) for institution in user.affiliated_institutions], [])

def format_contributor(preprint, user):
    return [{
        '@id': '_:{}-{}'.format(preprint._id, user._id),
        '@type': 'contributor',
        'person': {'@id': '_:{}'.format(user._id), '@type': 'person'},
        'creative_work': {'@id': '_:{}'.format(preprint._id), '@type': 'preprint'},
    }] + format_user(user)

def format_subjects(preprint):
    flat_subjs = []
    summed_subjs = sum(sum([[[{
        '@id': '_:{}'.format(subject['id']),
        '@type': 'subject',
        'name': subject['text']
    }, {
        '@id': '_:throughsubject-{}'.format(subject['id']),
        '@type': 'throughsubjects',
        'subject': {
            '@id': '_:{}'.format(subject['id']),
            '@type': 'subject',
        },
        'creative_work': {
            '@id': '_:{}'.format(preprint._id),
            '@type': 'preprint'
        }
    }] for subject in subject_hier] for subject_hier in preprint.get_subjects()], []), [])
    for s in summed_subjs:
        if s not in flat_subjs:
            flat_subjs.append(s)
    return flat_subjs

def format_doi(preprint):
    """
    * All DOIs will be valid URIs
    * All DOIs will use http
    * All DOI paths will be uppercased
    """
    return {
        '@id': '_:doi-{}'.format(preprint._id),
        '@type': 'link',
        'url': 'http://dx.doi.org/{}'.format(preprint.article_doi.upper().strip('/')),
        'type': 'doi'
    }

def format_preprint(preprint):
    preprint_parts = [
        {
            '@id': '_:{}'.format(preprint._id),
            '@type': 'preprint',
            'title': preprint.node.title,
            'description': preprint.node.description or '',
            'is_deleted': not preprint.is_published or not preprint.node.is_public or preprint.node.is_preprint_orphan
        }, {
            '@id': '_:link-{}'.format(preprint._id),
            '@type': 'link',
            'url': urlparse.urljoin(settings.DOMAIN, preprint.url),
            'type': 'provider'
        }
    ]

    if preprint.article_doi:
        preprint_parts.append(format_doi(preprint))

    return sum([preprint_parts] + [
        format_contributor(preprint, user) for user in preprint.node.contributors
    ] + [
        format_subjects(preprint)
    ] + [[{
        '@id': '_:{}-{}'.format(preprint._id, institution._id),
        '@type': 'association',
        'entity': {
            '@id': '_:{}'.format(institution._id),
            '@type': 'institution',
        },
        'creative_work': {
            '@id': '_:{}'.format(preprint._id),
            '@type': 'preprint',
        }
    }] + format_institution(institution) for institution in preprint.node.affiliated_institutions], [])
