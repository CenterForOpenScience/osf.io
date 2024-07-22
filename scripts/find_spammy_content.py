import io
import csv
import re
from datetime import timedelta
import logging

from django.db.models import Q
from django.utils import timezone
from osf.models import Node, Preprint, Registration

logger = logging.getLogger(__name__)

def manage_spammy_content(regex, days=1, models=[Node, Preprint, Registration], return_csv=True, ban=False, response_object=None, fast=False):
    script_start_time = timezone.now()
    logger.info(f'Script started time: {script_start_time}')
    data = []
    count = 0
    field_names = ['Object Type', 'GUID', 'Spam Content', 'Created', 'User ID', 'Username', 'Fullname']
    find_fn = find_spammy_content_fast if fast else find_spammy_content

    for model in models:
        data.extend(find_fn(regex, days, model, ban))
        count = count + len(data)

    script_finish_time = timezone.now()
    logger.info(f'Script finished time: {script_finish_time}')
    logger.info(f'Run time {script_finish_time - script_start_time}')

    if ban:
        logger.info(f'Banned {count} users')
        return count

    if return_csv:
        if response_object:
            output = response_object
        else:
            output = io.StringIO()
        writer = csv.writer(output, field_names)
        writer.writerow([field for field in field_names])
        for item in data:
            writer.writerow([
                item['type'],
                item['guid'],
                item['content'],
                item['created'],
                item['uid'],
                item['username'],
                item['fullname']
            ])
        return output
    else:
        return data

def find_spammy_content(regex, days, model, ban):
    check_fields = model.SPAM_CHECK_FIELDS.copy()
    created_items = model.objects.filter(created__gte=timezone.now() - timedelta(days=days))
    data = []
    for item in created_items:
        item_data = {}
        spam_fields = item.get_spam_fields(check_fields)
        spam_content = item._get_spam_content(spam_fields)
        matches = re.search(regex, spam_content, re.IGNORECASE)
        if matches:
            item_data['type'] = model.__name__
            item_data['guid'] = item._id
            item_data['content'] = spam_content
            item_data['created'] = item.created
            item_data['uid'] = item.creator._id
            item_data['username'] = item.creator.username
            item_data['fullname'] = item.creator.fullname
            data.append(item_data)
            if ban:
                item.suspend_spam_user(item.creator)
    return data

def find_spammy_content_fast(regex, days, model, ban):
    spam = model.objects.filter(
        (Q(title__iregex=regex)|Q(description__iregex=regex)) &
        Q(created__gte=timezone.now() - timedelta(days=days)) &
        ~Q(spam_status=2) &
        Q(deleted__isnull=True)
    )
    data = []
    for item in spam.values('guids___id', 'title', 'description', 'created', 'creator__guids___id', 'creator__username', 'creator__fullname'):
        item_data = {}
        item_data['type'] = model.__name__
        item_data['guid'] = item['guids___id']
        item_data['content'] = item['title'] + '::' + item['description']
        item_data['created'] = item['created']
        item_data['uid'] = item['creator__guids___id']
        item_data['username'] = item['creator__username']
        item_data['fullname'] = item['creator__fullname']
        data.append(item_data)
        if ban:
            model.load(item['guids___id']).suspend_spam_user(item['creator__guids___id'])
    return data
