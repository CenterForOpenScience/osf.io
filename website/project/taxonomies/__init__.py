from modularodm import fields

from framework.mongo import (
    ObjectId,
    StoredObject,
    utils as mongo_utils
)

from website.util import api_v2_url

@mongo_utils.unique_on(['text'])
class Subject(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    text = fields.StringField(required=True)
    parents = fields.ForeignField('subject', list=True)

    @property
    def absolute_api_v2_url(self):
        return api_v2_url('taxonomies/{}/'.format(self._id))

    def get_absolute_url(self):
        return self.absolute_api_v2_url
