from django.db import models

from .base import BaseModel

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

INSTITUTION_ASSET_NAME_CHOICES = [
    ('banner', 'banner'),
    ('logo', 'logo'),
    ('logo_rounded_corners', 'logo_rounded_corners'),
]

class AssetFile(BaseModel):
    class Meta:
        abstract = True
    file = models.FileField(upload_to='assets')

class ProviderAssetFile(AssetFile):
    class Meta:
        permissions = (
            # Clashes with built-in permissions
            # ('view_providerassetfile', 'Can view provider asset files'),
        )

    name = models.CharField(choices=PROVIDER_ASSET_NAME_CHOICES, max_length=63)
    providers = models.ManyToManyField('AbstractProvider', blank=True, related_name='asset_files')


class InstitutionAssetFile(AssetFile):
    name = models.CharField(choices=INSTITUTION_ASSET_NAME_CHOICES, max_length=63)
    institutions = models.ManyToManyField('Institution', blank=True, related_name='asset_files')
