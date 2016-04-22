

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
        'field_submission1': meeting.field_names['submission1'],
        'field_submission2': meeting.field_names['submission2'],
        'field_submission1_plural': meeting.field_names['submission1_plural'],
        'field_submission2_plural': meeting.field_names['submission2_plural'],
        'field_meeting_title_type': meeting.field_names['meeting_title_type'],
        'field_add_submission': meeting.field_names['add_submission'],
        'field_mail_subject': meeting.field_names['mail_subject'],
        'field_mail_message_body': meeting.field_names['mail_message_body'],
        'field_mail_attachment': meeting.field_names['mail_attachment'],
    }
