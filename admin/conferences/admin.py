from django.contrib import admin
from .models import Conference
# Register your models here.

class ConferenceAdmin(admin.ModelAdmin):
    search_fields = ['name', ]

admin.site.register(Conference, ConferenceAdmin)
