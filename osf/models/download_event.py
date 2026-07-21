from django.db import models


class DownloadEvent(models.Model):
    """One metadata row per download — never the file contents.

    Foundation for the download-telemetry capture and dashboard. Append-only:
    rows are written from the download flow (single files at the osf.io redirect
    view, folder/project zips from the WaterButler callback) and read, always
    scoped to a time range, by the dashboard.
    """

    FILE = 'file'
    FOLDER_ZIP = 'folder_zip'
    PROJECT = 'project'
    DOWNLOAD_TYPES = (
        (FILE, 'Single file'),
        (FOLDER_ZIP, 'Folder zip'),
        (PROJECT, 'Whole-project zip'),
    )

    created = models.DateTimeField(auto_now_add=True, db_index=True)

    # what was downloaded
    resource_guid = models.CharField(max_length=255, blank=True, default='', db_index=True)
    path = models.TextField(blank=True, default='')
    download_type = models.CharField(max_length=16, choices=DOWNLOAD_TYPES)
    # null for single files (only zips stream through WB, which reports completion)
    zip_completed = models.BooleanField(null=True, blank=True)
    size_bytes = models.BigIntegerField(default=0)

    # storage_region = where the bytes were served from (capacity);
    # user_region = roughly where the user is. Kept separate on purpose.
    storage_region = models.CharField(max_length=64, blank=True, default='')
    user_region = models.CharField(max_length=64, blank=True, default='')
    ip = models.GenericIPAddressField(null=True, blank=True)
    source_area = models.CharField(max_length=128, blank=True, default='')

    # nullable: anonymous downloads of public files
    user = models.ForeignKey(
        'osf.OSFUser',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='download_events',
    )

    class Meta:
        # `created` is indexed on the field; these cover the dashboard's
        # time-range group-bys.
        indexes = [
            models.Index(fields=['created', 'download_type'], name='download_event_crt_type'),
            models.Index(fields=['created', 'storage_region'], name='download_event_crt_regn'),
            models.Index(fields=['created', 'user_region'], name='download_event_crt_user'),
        ]

    def __repr__(self):
        return (
            f'<DownloadEvent(id={self.id}, user={self.user_id}, '
            f'type={self.download_type}, size_bytes={self.size_bytes})>'
        )

    def __str__(self):
        return self.__repr__()
