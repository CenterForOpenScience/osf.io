from website.conferences.model import DEFAULT_FIELD_NAMES

def serialize_meeting(meeting):
    is_meeting = True
    if hasattr(meeting, 'is_meeting') and meeting.is_meeting is not None:
        is_meeting = meeting.is_meeting
    return {
        'endpoint': meeting.endpoint,
        'name': meeting.name,
        'info_url': meeting.info_url,
        'homepage_link_text': meeting.field_names.get('homepage_link_text', DEFAULT_FIELD_NAMES.get('homepage_link_text', '')),
        'logo_url': meeting.logo_url,
        'active': meeting.active,
        'admins': ', '.join([u.username for u in meeting.admins]),
        'public_projects': meeting.public_projects,
        'poster': meeting.poster,
        'talk': meeting.talk,
        'num_submissions': meeting.num_submissions,
        'location': meeting.location,
        'start_date': meeting.start_date,
        'end_date': meeting.end_date,
        'submission1': meeting.field_names.get('submission1', DEFAULT_FIELD_NAMES.get('submission1', '')),
        'submission2': meeting.field_names.get('submission2', DEFAULT_FIELD_NAMES.get('submission2', '')),
        'submission1_plural': meeting.field_names.get('submission1_plural', DEFAULT_FIELD_NAMES.get('submission1_plural', '')),
        'submission2_plural': meeting.field_names.get('submission2_plural', DEFAULT_FIELD_NAMES.get('submission2_plural', '')),
        'meeting_title_type': meeting.field_names.get('meeting_title_type', DEFAULT_FIELD_NAMES.get('meeting_title_type', '')),
        'add_submission': meeting.field_names.get('add_submission', DEFAULT_FIELD_NAMES.get('add_submission', '')),
        'mail_subject': meeting.field_names.get('mail_subject', DEFAULT_FIELD_NAMES.get('mail_subject', '')),
        'mail_message_body': meeting.field_names.get('mail_message_body', DEFAULT_FIELD_NAMES.get('mail_message_body', '')),
        'mail_attachment': meeting.field_names.get('mail_attachment', DEFAULT_FIELD_NAMES.get('mail_attachment', '')),
        'is_meeting': is_meeting,
    }
