from django.db import models

from .base import BaseModel

class Tag(BaseModel):
    # TODO DELETE ME POST MIGRATION
    primary_identifier_name = 'name'
    modm_model_path = 'website.project.model.Tag'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    name = models.CharField(db_index=True, max_length=1024)
    system = models.BooleanField(default=False)

    def __unicode__(self):
        if self.system:
            return 'System Tag: {}'.format(self.name)
        return u'{}'.format(self.name)

    def _natural_key(self):
        return hash(self.name + str(self.system))

    @property
    def _id(self):
        return self.name.lower()

    @classmethod
    def load(cls, data):
        """For compatibility with v1: the tag name used to be the _id,
        so we make Tag.load('tagname') work as if `name` were the primary key.
        """
        try:
            return cls.objects.get(name=data)
        except cls.DoesNotExist:
            return None

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        """
        Given a modm object, make a django object with the same local fields.

        :param modm_obj:
        :return:
        """
        django_obj = cls()

        setattr(django_obj, 'name', modm_obj._id)

        return django_obj

    class Meta:
        unique_together = ('name', 'system')
