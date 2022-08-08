from django.db import models
from osf.models import base


class ExportDataRestore(base.BaseModel):
    export_id = models.ForeignKey("osf_export_data", unique=True)
    destination_id = models.ForeignKey("addons_osfstorage_region", unique=True)
    process_start = models.DateTimeField(auto_now=False, auto_now_add=False)
    process_end = models.DateTimeField(auto_now=False, auto_now_add=False)
    last_check = models.DateTimeField(auto_now=False, auto_now_add=False)
    status = models.CharField(max_length=255)
