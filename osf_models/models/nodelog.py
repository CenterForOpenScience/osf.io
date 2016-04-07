from django.db import models
from framework.mongo import ObjectId

class NodeLog(models.Model):
    id = models.AutoField(primary_key=True)
    guid = models.fields.CharField(max_length=255, unique=True, db_index=True, default=lambda: str(ObjectId()))
