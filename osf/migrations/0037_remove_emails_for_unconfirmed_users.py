# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-16 19:59
"""Removes Email objects that associated with unconfirmed users. These
were incorrectly created in 0033_user_emails_to_fk.
"""
from __future__ import unicode_literals

from django.db import migrations


def remove_emails(state, *args, **kwargs):
    Email = state.get_model('osf', 'email')
    Email.objects.filter(user__date_confirmed__isnull=True).delete()

# copied from 0033_user_emails_to_fk
def restore_emails(state, *args, **kwargs):
    Email = state.get_model('osf', 'email')
    OSFUser = state.get_model('osf', 'osfuser')
    for user in OSFUser.objects.filter(date_confirmed__isnull=True).values('id', 'username', 'is_active'):
        uid = user['id']
        primary_email = user['username'].lower().strip()
        active = user['is_active']
        if active or not Email.objects.filter(address=primary_email).exists():
            _, created = Email.objects.get_or_create(address=primary_email, user_id=uid)
            assert created, 'Email object for username {} already exists'.format(primary_email)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0036_auto_20170605_1520'),
    ]

    operations = [
        migrations.RunPython(
            remove_emails, restore_emails,
        ),
    ]
