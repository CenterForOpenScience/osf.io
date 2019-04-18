from include import IncludeManager

from osf.models.base import BaseModel, ObjectIDMixin
from website.util import api_v2_url


class BaseLog(ObjectIDMixin, BaseModel):

    class Meta:
        abstract = True

    objects = IncludeManager()

    @property
    def absolute_api_v2_url(self):
        path = '/logs/{}/'.format(self._id)
        return api_v2_url(path)

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def absolute_url(self):
        return self.absolute_api_v2_url

    def _natural_key(self):
        return self._id
