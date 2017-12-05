from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, DateByVersion


class BannerSerializer(JSONAPISerializer):

    #TODO: Wut to do with id?? Where my id's at?
    start_date = DateByVersion(read_only=True)
    end_date = DateByVersion(read_only=True)
    color = ser.CharField(read_only=True)
    license = ser.CharField(read_only=True)
    default_text = ser.SerializerMethodField()
    mobile_text = ser.SerializerMethodField()

    default_photo_url = ser.SerializerMethodField()
    mobile_photo_url = ser.SerializerMethodField()

    def get_default_photo_url(self, banner):
        if banner.default_photo:
            return banner.default_photo.url

    def get_mobile_photo_url(self, banner):
        if banner.mobile_photo:
            return banner.mobile_photo.url

    def get_default_text(self, banner):
        return self.add_license(banner, banner.default_text)

    def get_mobile_text(self, banner):
        if banner.mobile_text:
            return self.add_license(banner, banner.mobile_text)
        return self.get_default_text(banner)

    def add_license(self, banner, text):
        if banner.license:
            return text + ' Image copyright {}.'.format(banner.license)
        return text

    class Meta:
        type_ = 'banners'
