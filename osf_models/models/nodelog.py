from django.db import models
from framework.mongo import ObjectId
from osf_models.models import User
from osf_models.models.base import BaseModel
from osf_models.models import Node


class NodeLog(BaseModel):
    guid = models.fields.CharField(max_length=255, unique=True, db_index=True, default=lambda: str(ObjectId()))
    user = models.ForeignKey(User)
    node = models.ForeignKey(Node, related_name='logs')
