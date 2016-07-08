

def serialize_meeting(meeting):
    return {
        'endpoint': meeting.endpoint,
        'name': meeting.name,
        'info_url': meeting.info_url,
        'logo_url': meeting.logo_url,
        'active': meeting.active,
        'admins': ', '.join([u.emails[0] for u in meeting.admins]),
        'public_projects': meeting.public_projects,
        'poster': meeting.poster,
        'talk': meeting.talk,
        'num_submissions': meeting.num_submissions,
        'location': meeting.location,
        'start_date': meeting.start_date,
        'end_date': meeting.end_date,
        'submission1': meeting.field_names['submission1'],
        'submission2': meeting.field_names['submission2'],
        'submission1_plural': meeting.field_names['submission1_plural'],
        'submission2_plural': meeting.field_names['submission2_plural'],
        'meeting_title_type': meeting.field_names['meeting_title_type'],
        'add_submission': meeting.field_names['add_submission'],
        'mail_subject': meeting.field_names['mail_subject'],
        'mail_message_body': meeting.field_names['mail_message_body'],
        'mail_attachment': meeting.field_names['mail_attachment'],
    }
