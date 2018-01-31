from api.base.utils import absolute_reverse
from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, VersionedDateTimeField, LinksField


class BannerSerializer(JSONAPISerializer):

    start_date = VersionedDateTimeField(read_only=True)
    end_date = VersionedDateTimeField(read_only=True)
    color = ser.CharField(read_only=True)
    license = ser.CharField(read_only=True)
    default_alt_text = ser.SerializerMethodField()
    mobile_alt_text = ser.SerializerMethodField()

    links = LinksField({
        'self': 'get_absolute_url',
        'default_photo': 'get_default_photo_url',
        'mobile_photo': 'get_mobile_photo_url',
    })

    def get_default_photo_url(self, banner):
        if banner.default_photo:
            return banner.default_photo.url

    def get_mobile_photo_url(self, banner):
        if banner.mobile_photo:
            return banner.mobile_photo.url

    def get_default_alt_text(self, banner):
        return self.add_license(banner, banner.default_alt_text)

    def get_mobile_alt_text(self, banner):
        if banner.mobile_alt_text:
            return self.add_license(banner, banner.mobile_alt_text)
        return self.get_default_alt_text(banner)

    def add_license(self, banner, text):
        if banner.license and not banner.license.lower() == 'none':
            return text + ' Image copyright {}.'.format(banner.license)
        return text

    # Only the current banner's URL is surfaced through the API
    # Individual banners are not accessible publicly
    def get_absolute_url(self, obj):
        return absolute_reverse('banners:current')

    class Meta:
        type_ = 'banners'
