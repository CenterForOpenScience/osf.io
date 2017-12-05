import urlparse
from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, DateByVersion


class BannerSerializer(JSONAPISerializer):

    #TODO: Wut to do with id?? Where my id's at?
    start_date = DateByVersion(read_only=True)
    end_date = DateByVersion(read_only=True)
    color = ser.CharField(required=True)
    license = ser.CharField()
    alt = ser.CharField(required=True)

    default_photo_url = ser.SerializerMethodField()
    mobile_photo_url = ser.SerializerMethodField()

    def get_default_photo_url(self, banner):
        return urlparse.urljoin(banner.media_base_url, banner.default_photo.url)

    def get_mobile_photo_url(self, banner):
        return urlparse.urljoin(banner.media_base_url, banner.mobile_photo.url)

    class Meta:
        type_ = 'banners'
