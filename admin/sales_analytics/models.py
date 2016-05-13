from admin.metrics.utils import get_list_of_dates
from datetime import datetime, timedelta
from django.db import models


class UserCount(models.Model):
    class Meta:
        unique_together = (('date', 'tag'),)

    date = models.DateField(auto_now_add=True)
    tag = models.TextField()
    count = models.IntegerField()
    percent = models.FloatField()

    @staticmethod
    def get_user_count(date):
        from .utils import get_sorted_index
        try:
            results = UserCount.objects.filter(date=date)
            count_list = [result.count for result in results]
            sorted_index = get_sorted_index(count_list)
            count_list = [count_list[i] for i in sorted_index]
            percent_list = [results[i].percent for i in sorted_index]
            tags = [results[i].tag for i in sorted_index]
            return {'tags': tags,
                    'count': count_list,
                    'percent': percent_list,
                    'total': sum(count_list)}
        except UserCount.DoesNotExist:
            return

    @staticmethod
    def get_count_history(tag, start=datetime.now().date() - timedelta(days=30), end=datetime.now().date()):
        results = UserCount.objects.filter(tag=tag, date__gte=start, date__lte=end)
        x = ['x', ]
        data = ['data', ]

        for result in results:
            x.append

    @staticmethod
    def save_record(result_dict):
        total = result_dict.pop('total', None)
        for i in range(len(result_dict['tags'])):
            uc = UserCount(tag=result_dict['tags'][i],
                           count=result_dict['count'][i],
                           percent=result_dict['percent'][i])
            uc.save()


class DBMetrics(models.Model):
    class Meta:
        unique_together = (('date', 'name'),)
    date = models.DateField(auto_now_add=True)
    name = models.TextField()
    data = models.TextField()

    @staticmethod
    def get_record(date, names):
        try:
            results = DBMetrics.objects.filter(date=date,
                                               name__in=names)
            record = {}
            for result in results:
                record[result.name] = result.data
            return record
        except DBMetrics.DoesNotExist:
            return None

    @staticmethod
    def save_record(result_dict):
        for key, value in result_dict.items():
            metric = DBMetrics(name=key,
                               data=value)
            metric.save()
