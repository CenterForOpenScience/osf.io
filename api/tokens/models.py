import uuid
import datetime
import urlparse

from modularodm import fields
from website import settings

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

    @property
    def url(self):
        return '/settings/tokens/{}/'.format(self._id)

    @property
    def absolute_url(self):
        return urlparse.urljoin(settings.DOMAIN, self.url)
