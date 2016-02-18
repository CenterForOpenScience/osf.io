from __future__ import unicode_literals
from modularodm import fields, Q


from django.db import models


# Create your models here.
class Conference(models.Model):
    #: Determines the email address for submission and the OSF url
    # Example: If endpoint is spsp2014, then submission email will be
    # spsp2014-talk@osf.io or spsp2014-poster@osf.io and the OSF url will
    # be osf.io/view/spsp2014

    endpoint = models.CharField(primary_key=True, max_length=30, blank=False, unique=True)
    #: Full name, e.g. "SPSP 2014"
    name = models.CharField(max_length=30, blank=False)
    info_url = models.CharField(max_length=200, blank=True, default=None)
    logo_url = models.CharField(max_length=200, blank=True, default=None)
    active = models.BooleanField(blank=False)
    admins = models.CharField(max_length=200, blank=False, default=None)

    #: Whether to make submitted projects public
    public_projects = models.BooleanField(blank=True, default=True)
    poster = models.BooleanField(default=True)
    talk = models.BooleanField(default=True)

    # [TODO] field_names are used to customize the text on the conference page, the categories
    # of submissions, and the email adress to send material to.
    # field_names = fields.DictionaryField(
    #     default=lambda: {
    #         'submission1': 'poster',
    #         'submission2': 'talk',
    #         'submission1_plural': 'posters',
    #         'submission2_plural': 'talks',
    #         'meeting_title_type': 'Posters & Talks',
    #         'add_submission': 'poster or talk',
    #         'mail_subject': 'Presentation title',
    #         'mail_message_body': 'Presentation abstract (if any)',
    #         'mail_attachment': 'Your presentation file (e.g., PowerPoint, PDF, etc.)'
    #     }
    # Cached number of submissions
    num_submissions = models.IntegerField(default=0)


    # @classmethod
    # def get_by_endpoint(cls, endpoint, active=True):
    #     query = Q('endpoint', 'iexact', endpoint)
    #     if active:
    #         query &= Q('active', 'eq', True)
    #     try:
    #         return Conference.find_one(query)
    #     except ModularOdmException:
    #         raise ConferenceError('Endpoint {0} not found'.format(endpoint))

    class Meta:
        ordering = ['endpoint']


class ConferenceFieldNames(models.Model):
    key = models.CharField(max_length=200)
    value = models.CharField(max_length=200)
    conference = models.ForeignKey('conference', blank=False)
