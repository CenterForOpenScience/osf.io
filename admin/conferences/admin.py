from django.contrib import admin
from .models import Conference, ConferenceFieldNames
# Register your models here.

class ConferenceAdmin(admin.ModelAdmin):
    search_fields = ['name', ]
    list_display = ['name', ]

class ConferenceFieldNamesAdmin(admin.ModelAdmin):
    search_fields = ['pub_date', ]
    list_display = ['submission1', ]

admin.site.register(Conference, ConferenceAdmin)
admin.site.register(ConferenceFieldNames, ConferenceFieldNamesAdmin)
