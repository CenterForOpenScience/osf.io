from django.db import models
from datetime import datetime

from osf.utils.storage import BannerImageStorage

from osf.exceptions import ValidationValueError
from osf.utils.fields import NonNaiveDateTimeField


def validate_banner_dates(banner_id, start_date, end_date):
    if start_date > end_date:
        raise ValidationValueError('Start date must be before end date.')

    overlapping = ScheduledBanner.objects.filter(
        (models.Q(start_date__gte=start_date) & models.Q(start_date__lte=end_date)) |
        (models.Q(end_date__gte=start_date) & models.Q(end_date__lte=end_date)) |
        (models.Q(start_date__lte=start_date) & models.Q(end_date__gte=end_date))
    ).exclude(id=banner_id).exists()

    if overlapping:
        raise ValidationValueError('Banners dates cannot be overlapping.')

class ScheduledBanner(models.Model):

    class Meta:
        # Custom permissions for use in the OSF Admin App
        permissions = (
            ('view_scheduledbanner', 'Can view scheduled banner details'),
        )

    name = models.CharField(unique=True, max_length=256)
    start_date = NonNaiveDateTimeField()
    end_date = NonNaiveDateTimeField()
    color = models.CharField(max_length=7)
    license = models.CharField(blank=True, null=True, max_length=256)
    link = models.URLField(blank=True, default='https://www.crowdrise.com/centerforopenscience')

    default_photo = models.FileField(storage=BannerImageStorage())
    default_alt_text = models.TextField()

    mobile_photo = models.FileField(storage=BannerImageStorage())
    mobile_alt_text = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.start_date = datetime.combine(self.start_date, datetime.min.time())
        self.end_date = datetime.combine(self.end_date, datetime.max.time())
        validate_banner_dates(self.id, self.start_date, self.end_date)
        super(ScheduledBanner, self).save(*args, **kwargs)
