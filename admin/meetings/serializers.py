

def serialize_meeting(meeting):
    return {
        'endpoint': meeting.endpoint,
        'name': meeting.name,
        'info_url': meeting.info_url,
        'logo_url': meeting.logo_url,
        'active': meeting.active,
        'admins': [u.emails[0] for u in meeting.admins],
        'public_projects': meeting.public_projects,
        'poster': meeting.poster,
        'talk': meeting.talk,
        'num_submissions': meeting.num_submissions,
        'field_sub1': meeting.field_names['submission1'],
        #continue field serialization
    }
