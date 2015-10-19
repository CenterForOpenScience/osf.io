import uuid
import datetime
import urlparse

from modularodm import fields
from website import settings
from api.base.utils import absolute_reverse

from framework.mongo import ObjectId, StoredObject

#from website.oauth.models import ApiOAuth2Scope

class ApiOAuth2PersonalToken(StoredObject):
    """
    Store information about recognized OAuth2 scopes. Only scopes registered under this database model can
        be requested by third parties.
    """
    _id = fields.StringField(primary=True,
                             default=lambda: str(ObjectId()))

    token_id = fields.StringField(default=lambda: uuid.uuid4().hex,  # Not *guaranteed* unique, but very unlikely
                               unique=True)

    owner = fields.ForeignField('User',
                                backref='created',
                                index=True,
                                required=True)

    name = fields.StringField(required=True, index=True)

    scopes = fields.StringField(list=True, required=True)

    date_last_used = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow,
                                        editable=False)

    is_active = fields.BooleanField(default=True, index=True)  # TODO: Add mechanism to deactivate a scope?

    def deactivate(self, save=False):
        """
        Deactivate an ApiOAuth2PersonalToken

        Does not delete the database record, but hides this instance from API
        """
        self.is_active = False

        if save:
            self.save()
        return True

    @property
    def url(self):
        return '/settings/tokens/{}/'.format(self._id)

    @property
    def absolute_url(self):
        return urlparse.urljoin(settings.DOMAIN, self.url)

    # Properties used by Django and DRF "Links: self" field
    @property
    def absolute_api_v2_url(self):
        return absolute_reverse('tokens:token-detail', kwargs={'_id': self._id})

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url
