from django.db import models
from framework.mongo import ObjectId
from osf_models.models.base import BaseModel

def get_object_id():
    return str(ObjectId())


class NodeLog(BaseModel):
    guid = models.fields.CharField(max_length=255, unique=True, db_index=True, default=get_object_id)
    user = models.ForeignKey('User', related_name='logs')
    node = models.ForeignKey('Node', related_name='logs')
