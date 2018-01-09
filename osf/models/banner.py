from django.db import models

from osf.utils.storage import BannerImageStorage

from osf.exceptions import ValidationValueError
from osf.utils.fields import NonNaiveDateTimeField


class ScheduledBanner(models.Model):

    class Meta:
        # Custom permissions for use in the OSF Admin App
        permissions = (
            ('view_banner', 'Can view banner details'),
            ('change_banner', 'Can change banner details'),
            ('delete_banner', 'Can delete banner'),
        )

    start_date = NonNaiveDateTimeField()
    end_date = NonNaiveDateTimeField()
    color = models.TextField()
    license = models.TextField(blank=True, null=True)

    default_photo = models.FileField(storage=BannerImageStorage())
    default_text = models.TextField()

    mobile_photo = models.FileField(storage=BannerImageStorage())
    mobile_text = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.start_date > self.end_date:
            raise ValidationValueError('Start date must be before end date.')

        overlapping = ScheduledBanner.objects.filter(
            (models.Q(start_date__gte=self.start_date) & models.Q(start_date__lt=self.end_date)) |
            (models.Q(end_date__gt=self.start_date) & models.Q(end_date__lte=self.end_date)) |
            (models.Q(start_date__lt=self.start_date) & models.Q(end_date__gt=self.end_date))
        ).exclude(id=self.id).exists()

        if overlapping:
            raise ValidationValueError('Banners dates cannot be overlapping.')
        else:
            super(ScheduledBanner, self).save(*args, **kwargs)
