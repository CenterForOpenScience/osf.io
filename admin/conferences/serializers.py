

def serialize_conference(conference):
    return {
        'name': conference.name,
        'endpoint': conference.endpoint,
        'active': conference.active,
        'public_projects': conference.public_projects,
        'poster': conference.poster,
        'talk': conference.talk,
    }
