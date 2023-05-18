# Generated by Django 3.2.17 on 2023-05-08 19:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.models.base
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0011_institution_rework_post_release'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSessionMap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('session_key', models.CharField(max_length=255)),
                ('expire_date', osf.utils.fields.NonNaiveDateTimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'session_key')},
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
        migrations.DeleteModel(
            name='Session',
        ),
    ]