from django.db import models

from osf.utils.storage import BannerImageStorage

from osf.exceptions import ValidationValueError
from osf.utils.fields import NonNaiveDateTimeField


def validate_banner_dates(banner_id, start_date, end_date):
    if start_date > end_date:
        raise ValidationValueError('Start date must be before end date.')

    overlapping = ScheduledBanner.objects.filter(
        (models.Q(start_date__gte=start_date) & models.Q(start_date__lt=end_date)) |
        (models.Q(end_date__gt=start_date) & models.Q(end_date__lte=end_date)) |
        (models.Q(start_date__lt=start_date) & models.Q(end_date__gt=end_date))
    ).exclude(id=banner_id).exists()

    if overlapping:
        raise ValidationValueError('Banners dates cannot be overlapping.')

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
        validate_banner_dates(self.id, self.start_date, self.end_date)
        super(ScheduledBanner, self).save(*args, **kwargs)
