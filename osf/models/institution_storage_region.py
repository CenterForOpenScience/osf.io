from django.db import models

from osf.models.base import BaseModel


class InstitutionStorageRegion(BaseModel):

    institution = models.ForeignKey('Institution', on_delete=models.CASCADE)
    storage_region = models.ForeignKey('addons_osfstorage.Region', on_delete=models.CASCADE)
    is_preferred = models.BooleanField(default=False)

    class Meta:
        unique_together = ('institution', 'storage_region')

    def __repr__(self):
        return f'<{self.__class__.__name__}(institution={self.institution._id}, ' \
               f'storage_region={self.storage_region._id}, is_preferred={self.is_preferred}>'

    def __str__(self):
        return f'{self.institution._id}::{self.storage_region._id}::{self.is_preferred}'
