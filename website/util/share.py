import logging
import uuid
import urlparse

from website import settings


logger = logging.getLogger(__name__)


class GraphNode(object):

    @property
    def ref(self):
        return {'@id': self.id, '@type': self.type}

    def __init__(self, type_, **attrs):
        self.id = '_:{}'.format(uuid.uuid4())
        self.type = type_.lower()
        self.attrs = attrs

    def get_related(self):
        for value in self.attrs.values():
            if isinstance(value, GraphNode):
                yield value
            elif isinstance(value, list):
                for val in value:
                    yield val

    def serialize(self):
        ser = {}
        for key, value in self.attrs.items():
            if isinstance(value, GraphNode):
                ser[key] = value.ref
            elif isinstance(value, list) or value in {None, ''}:
                continue
            else:
                ser[key] = value

        return dict(self.ref, **ser)


def format_user(user):
    person = GraphNode('person', **{
        'suffix': user.suffix,
        'given_name': user.given_name,
        'family_name': user.family_name,
        'additional_name': user.middle_names,
    })

    person.attrs['identifiers'] = [GraphNode('agentidentifier', agent=person, uri='mailto:{}'.format(uri)) for uri in user.emails]

    if user.is_registered:
        person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=user.profile_image_url()))
        person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=urlparse.urljoin(settings.DOMAIN, user.profile_url)))

    person.attrs['related_agents'] = [GraphNode('isaffiliatedwith', subject=person, related=GraphNode('institution', name=institution.name)) for institution in user.affiliated_institutions.all()]

    return person


def format_contributor(preprint, user, bibliographic, index):
    return GraphNode(
        'creator' if bibliographic else 'contributor',
        agent=format_user(user),
        order_cited=index if bibliographic else None,
        creative_work=preprint,
        cited_as=user.fullname,
    )
