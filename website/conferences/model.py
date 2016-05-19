# -*- coding: utf-8 -*-

import bson
from modularodm import fields, Q
from modularodm.exceptions import ModularOdmException

from framework.mongo import StoredObject
from website.conferences.exceptions import ConferenceError


class Conference(StoredObject):
    #: Determines the email address for submission and the OSF url
    # Example: If endpoint is spsp2014, then submission email will be
    # spsp2014-talk@osf.io or spsp2014-poster@osf.io and the OSF url will
    # be osf.io/view/spsp2014
    endpoint = fields.StringField(primary=True, required=True, unique=True)
    #: Full name, e.g. "SPSP 2014"
    name = fields.StringField(required=True)
    info_url = fields.StringField(required=False, default=None)
    logo_url = fields.StringField(required=False, default=None)
    location = fields.StringField(required=False, default=None)
    start_date = fields.DateTimeField(default=None)
    end_date = fields.DateTimeField(default=None)
    active = fields.BooleanField(required=True)
    admins = fields.ForeignField('user', list=True, required=False, default=None)
    #: Whether to make submitted projects public
    public_projects = fields.BooleanField(required=False, default=True)
    poster = fields.BooleanField(default=True)
    talk = fields.BooleanField(default=True)
    # field_names are used to customize the text on the conference page, the categories
    # of submissions, and the email adress to send material to.
    field_names = fields.DictionaryField(
        default=lambda: {
            'submission1': 'poster',
            'submission2': 'talk',
            'submission1_plural': 'posters',
            'submission2_plural': 'talks',
            'meeting_title_type': 'Posters & Talks',
            'add_submission': 'poster or talk',
            'mail_subject': 'Presentation title',
            'mail_message_body': 'Presentation abstract (if any)',
            'mail_attachment': 'Your presentation file (e.g., PowerPoint, PDF, etc.)'
        }
    )

    # Cached number of submissions
    num_submissions = fields.IntegerField(default=0)

    @classmethod
    def get_by_endpoint(cls, endpoint, active=True):
        query = Q('endpoint', 'iexact', endpoint)
        if active:
            query &= Q('active', 'eq', True)
        try:
            return Conference.find_one(query)
        except ModularOdmException:
            raise ConferenceError('Endpoint {0} not found'.format(endpoint))


class MailRecord(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))
    data = fields.DictionaryField()
    records = fields.AbstractForeignField(list=True)
