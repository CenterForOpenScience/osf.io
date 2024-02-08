from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.models.base


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0004_django3_upgrade'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RenameModel('NotableEmailDomain', 'NotableDomain'),
        migrations.AlterField(
            model_name='notabledomain',
            name='note',
            field=models.IntegerField(choices=[(0, 'EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT'), (1, 'ASSUME_HAM_UNTIL_REPORTED'), (2, 'UNKNOWN'), (3, 'IGNORED')], default=2),
        ),
        migrations.CreateModel(
            name='DomainReference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('referrer_object_id', models.PositiveIntegerField()),
                ('is_triaged', models.BooleanField(default=False)),
                ('domain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='osf.NotableDomain')),
                ('referrer_content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
        migrations.AlterUniqueTogether(
            name='domainreference',
            unique_together={('referrer_object_id', 'domain')},
        ),
    ]
