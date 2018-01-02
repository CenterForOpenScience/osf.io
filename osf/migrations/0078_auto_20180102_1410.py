# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-02 20:10
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0077_merge_20180102_1409'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basefilenode',
            name='type',
            field=models.CharField(choices=[('osf.trashedfilenode', 'trashed file node'), ('osf.trashedfile', 'trashed file'), ('osf.trashedfolder', 'trashed folder'), ('osf.osfstoragefilenode', 'osf storage file node'), ('osf.osfstoragefile', 'osf storage file'), ('osf.osfstoragefolder', 'osf storage folder'), ('osf.bitbucketfilenode', 'bitbucket file node'), ('osf.bitbucketfolder', 'bitbucket folder'), ('osf.bitbucketfile', 'bitbucket file'), ('osf.boxfilenode', 'box file node'), ('osf.boxfolder', 'box folder'), ('osf.boxfile', 'box file'), ('osf.dataversefilenode', 'dataverse file node'), ('osf.dataversefolder', 'dataverse folder'), ('osf.dataversefile', 'dataverse file'), ('osf.dropboxfilenode', 'dropbox file node'), ('osf.dropboxfolder', 'dropbox folder'), ('osf.dropboxfile', 'dropbox file'), ('osf.cloudfilesfilenode', 'cloud files file node'), ('osf.cloudfilesfolder', 'cloud files folder'), ('osf.cloudfilesfile', 'cloud files file'), ('osf.figsharefilenode', 'figshare file node'), ('osf.figsharefolder', 'figshare folder'), ('osf.figsharefile', 'figshare file'), ('osf.githubfilenode', 'github file node'), ('osf.githubfolder', 'github folder'), ('osf.githubfile', 'github file'), ('osf.gitlabfilenode', 'git lab file node'), ('osf.gitlabfolder', 'git lab folder'), ('osf.gitlabfile', 'git lab file'), ('osf.googledrivefilenode', 'google drive file node'), ('osf.googledrivefolder', 'google drive folder'), ('osf.googledrivefile', 'google drive file'), ('osf.onedrivefilenode', 'one drive file node'), ('osf.onedrivefolder', 'one drive folder'), ('osf.onedrivefile', 'one drive file'), ('osf.owncloudfilenode', 'owncloud file node'), ('osf.owncloudfolder', 'owncloud folder'), ('osf.owncloudfile', 'owncloud file'), ('osf.s3filenode', 's3 file node'), ('osf.s3folder', 's3 folder'), ('osf.s3file', 's3 file')], db_index=True, max_length=255),
        ),
    ]
