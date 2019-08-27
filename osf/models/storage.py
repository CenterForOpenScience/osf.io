
from django.db import models

from osf.models.base import BaseModel

PROVIDER_ASSET_NAME_CHOICES = [
    ('favicon', 'favicon'),
    ('powered_by_share', 'powered_by_share'),
    ('sharing', 'sharing'),
    ('square_color_no_transparent', 'square_color_no_transparent'),
    ('square_color_transparent', 'square_color_transparent'),
    ('style', 'style'),
    ('wide_black', 'wide_black'),
    ('wide_color', 'wide_color'),
    ('wide_white', 'wide_white'),
]

class ProviderAssetFile(BaseModel):
    class Meta:
        permissions = (
            ('view_providerassetfile', 'Can view provider asset files'),
        )

    name = models.CharField(choices=PROVIDER_ASSET_NAME_CHOICES, max_length=63)
    file = models.FileField(upload_to='assets')
    providers = models.ManyToManyField('AbstractProvider', blank=True, related_name='asset_files')


class StorageType(BaseModel):
    class Meta:
        abstract = True

    NII_STORAGE = 1
    CUSTOM_STORAGE = 2

    STORAGE_TYPE_CHOICES = (
        (NII_STORAGE, 'NII Storage'),
        (CUSTOM_STORAGE, 'Custom Storage'),
    )
