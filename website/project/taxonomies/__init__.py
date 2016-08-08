from modularodm import fields

from framework.mongo import (
    ObjectId,
    StoredObject,
    utils as mongo_utils
)


@mongo_utils.unique_on(['id', '_id'])
class Subject(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    type = fields.StringField(required=True)
    text = fields.StringField(required=True)
    parent_ids = fields.StringField(list=True)

    def get_absolute_url(self):
        return '{}taxonomies/{}/?filter[id]={}'.format(self.absolute_api_v2_url, self.type, self._id)
