import uuid


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

    person.attrs['identifiers'] = [GraphNode('agentidentifier', agent=person, uri='mailto:{}'.format(uri)) for uri in user.emails.values_list('address', flat=True)]
    person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=user.absolute_url))

    if user.external_identity.get('ORCID') and user.external_identity['ORCID'].values()[0] == 'VERIFIED':
        person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=list(user.external_identity['ORCID'].keys())[0]))

    if user.is_registered:
        person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=user.profile_image_url()))

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

def format_subject(subject, context=None):
    if context is None:
        context = {}
    if subject is None:
        return None
    if subject.id in context:
        return context[subject.id]
    context[subject.id] = GraphNode(
        'subject',
        name=subject.text,
        is_deleted=False,
        uri=subject.absolute_api_v2_url,
    )
    context[subject.id].attrs['parent'] = format_subject(subject.parent, context)
    context[subject.id].attrs['central_synonym'] = format_subject(subject.bepress_subject, context)
    return context[subject.id]
