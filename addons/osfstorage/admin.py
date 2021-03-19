from django.contrib import admin
from osf.models.region import Region


class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', '_id', 'waterbutler_url', 'mfr_url']

admin.site.register(Region, RegionAdmin)
