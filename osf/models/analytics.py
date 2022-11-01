import logging

from dateutil import parser
from django.db import models, transaction
from django.db.models import Sum
from django.db.models.expressions import RawSQL
from django.utils import timezone

from framework.sessions import session
from osf.models.base import BaseModel, Guid
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField

logger = logging.getLogger(__name__)


class UserActivityCounter(BaseModel):
    primary_identifier_name = '_id'

    _id = models.CharField(max_length=5, null=False, blank=False, db_index=True,
                           unique=True)  # 5 in prod
    action = DateTimeAwareJSONField(default=dict)
    date = DateTimeAwareJSONField(default=dict)
    total = models.PositiveIntegerField(default=0)

    @classmethod
    def get_total_activity_count(cls, user_id):
        try:
            return cls.objects.get(_id=user_id).total
        except cls.DoesNotExist:
            return 0

    @classmethod
    def increment(cls, user_id, action, date_string):
        date = parser.parse(date_string).strftime('%Y/%m/%d')
        with transaction.atomic():
            # select_for_update locks the row but only inside a transaction
            uac, created = cls.objects.select_for_update().get_or_create(_id=user_id)
            if uac.total > 0:
                uac.total += 1
            else:
                uac.total = 1
            if action in uac.action:
                uac.action[action]['total'] += 1
                if date in uac.action[action]['date']:
                    uac.action[action]['date'][date] += 1
                else:
                    uac.action[action]['date'][date] = 1
            else:
                uac.action[action] = dict(total=1, date={date: 1})
            if date in uac.date:
                uac.date[date]['total'] += 1
            else:
                uac.date[date] = dict(total=1)
            uac.save()
        return True


class PageCounter(BaseModel):
    primary_identifier_name = '_id'

    _id = models.CharField(max_length=300, null=False, blank=False, db_index=True,
                           unique=True)  # 272 in prod

    date = DateTimeAwareJSONField(default=dict)

    total = models.PositiveIntegerField(default=0)
    unique = models.PositiveIntegerField(default=0)

    action = models.CharField(max_length=128, null=False, blank=False)
    resource = models.ForeignKey(Guid, related_name='pagecounters', null=False, blank=False, on_delete=models.CASCADE)
    file = models.ForeignKey('osf.BaseFileNode', null=False, blank=False, related_name='pagecounters', on_delete=models.CASCADE)
    version = models.IntegerField(null=True, blank=True)

    @classmethod
    def get_all_downloads_on_date(cls, date):
        """
        Queries the total number of downloads on a date
        :param str date: must be formatted the same as a page counter key so 'yyyy/mm/dd'
        :return: long sum:
        """
        formatted_date = date.strftime('%Y/%m/%d')
        # Get all PageCounters with data for the date made for all versions downloads - don't include specific versions
        page_counters = cls.objects.filter(date__has_key=formatted_date, version__isnull=True, action='download')

        # Get the total download numbers from the nested dict on the PageCounter by annotating it as daily_total then
        # aggregating the sum.
        daily_total = page_counters.annotate(daily_total=RawSQL("((date->%s->>'total')::int)", (formatted_date,))).aggregate(sum=Sum('daily_total'))['sum']

        return daily_total

    @staticmethod
    def clean_page(page):
        return page.replace(
            '.', '_'
        ).replace(
            '$', '_'
        )

    @classmethod
    def update_counter(cls, resource, file, version, action, node_info):
        if version is not None:
            page = '{0}:{1}:{2}:{3}'.format(action, resource._id, file._id, version)
        else:
            page = '{0}:{1}:{2}'.format(action, resource._id, file._id)

        cleaned_page = cls.clean_page(page)
        date = timezone.now()
        date_string = date.strftime('%Y/%m/%d')
        visited_by_date = session.data.get('visited_by_date', {'date': date_string, 'pages': []})
        with transaction.atomic():
            # Temporary backwards compat - when creating new PageCounters, temporarily keep writing to _id field.
            # After we're sure this is stable, we can stop writing to the _id field, and query on
            # resource/file/action/version
            model_instance, created = cls.objects.select_for_update().get_or_create(
                _id=cleaned_page,
                resource=resource,
                file=file,
                action=action,
                version=version
            )

            # if they visited something today
            if date_string == visited_by_date['date']:
                # if they haven't visited this page today
                if cleaned_page not in visited_by_date['pages']:
                    # if the model_instance has today in it
                    if date_string in model_instance.date.keys():
                        # increment the number of unique visitors for today
                        model_instance.date[date_string]['unique'] += 1
                    else:
                        # set the number of unique visitors for today to 1
                        model_instance.date[date_string] = dict(unique=1)
            # if they haven't visited something today
            else:
                # set their visited by date to blank
                visited_by_date['date'] = date_string
                visited_by_date['pages'] = []
                # if the model_instance has today in it
                if date_string in model_instance.date.keys():
                    # increment the number of unique visitors for today
                    model_instance.date[date_string]['unique'] += 1
                else:
                    # set the number of unique visitors to 1
                    model_instance.date[date_string] = dict(unique=1)

            # update their sessions
            visited_by_date['pages'].append(cleaned_page)
            session.data['visited_by_date'] = visited_by_date

            if date_string in model_instance.date.keys():
                if 'total' not in model_instance.date[date_string].keys():
                    model_instance.date[date_string].update(total=0)
                model_instance.date[date_string]['total'] += 1
            else:
                model_instance.date[date_string] = dict(total=1)

            # if a download counter is being updated, only perform the update
            # if the user who is downloading isn't a contributor to the project
            page_type = cleaned_page.split(':')[0]
            if page_type in ('download', 'view') and node_info:
                if node_info['contributors'].filter(guids___id__isnull=False, guids___id=session.data.get('auth_user_id')).exists():
                    model_instance.save()
                    return

            visited = session.data.get('visited', [])
            if page not in visited:
                model_instance.unique += 1
                visited.append(page)
                session.data['visited'] = visited

            session.save()
            model_instance.total += 1

            model_instance.save()

    @classmethod
    def get_basic_counters(cls, resource, file, version, action):
        try:
            counter = cls.objects.get(resource=resource, file=file, version=version, action=action)
            return (counter.unique, counter.total)
        except cls.DoesNotExist:
            return (None, None)
