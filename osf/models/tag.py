from django.db import models

from .base import BaseModel


class TagManager(models.Manager):
    """Manager that filters out system tags by default.
    """

    def get_queryset(self):
        return super(TagManager, self).get_queryset().filter(system=False)

class Tag(BaseModel):
    name = models.CharField(db_index=True, max_length=1024)
    system = models.BooleanField(default=False)

    objects = TagManager()
    all_tags = models.Manager()

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
    def load(cls, data, system=False):
        """For compatibility with v1: the tag name used to be the _id,
        so we make Tag.load('tagname') work as if `name` were the primary key.
        """
        try:
            return cls.all_tags.get(system=system, name=data)
        except cls.DoesNotExist:
            return None

    class Meta:
        unique_together = ('name', 'system')
        ordering = ('name', )
