
from django.db import models

from osf.models.base import BaseModel


class ProviderAssetFile(BaseModel):
    name = models.CharField(max_length=63)
    file = models.FileField(upload_to='assets')
    providers = models.ManyToManyField('AbstractProvider', blank=True, related_name='asset_files')
