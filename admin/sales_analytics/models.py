from admin.base.settings import ENTRY_POINTS
from admin.metrics.utils import get_list_of_dates
from datetime import datetime, timedelta
from django.db import models


class UserCount(models.Model):
    class Meta:
        unique_together = (('date', 'tag'),)

    date = models.DateField(default=datetime.now().date())
    tag = models.TextField()
    count = models.IntegerField()
    percent = models.FloatField()

    @classmethod
    def get_user_count(cls, date):
        from .utils import get_sorted_index
        try:
            results = cls.objects.filter(date=date)
            if not results:
                return
            else:
                count_list = [result.count for result in results]
                sorted_index = get_sorted_index(count_list)
                count_list = [count_list[i] for i in sorted_index]
                percent_list = [results[i].percent for i in sorted_index]
                tags = [results[i].tag for i in sorted_index]
                return {'tags': tags,
                        'count': count_list,
                        'percent': percent_list,
                        'total': sum(count_list)}
        except cls.DoesNotExist:
            return

    @classmethod
    def get_product_count_history(cls, tag, start=datetime.now().date() - timedelta(days=30), end=datetime.now().date()):
        results = cls.objects.filter(tag=tag, date__gte=start, date__lte=end)
        x = ['x', ]
        data = [tag, ]

        for result in results:
            x.append(result.date.strftime('%Y-%m-%d'))
            data.append(result.count)
        return [x, data]

    @classmethod
    def get_count_history(cls, entry_points=ENTRY_POINTS, start=datetime.now().date() - timedelta(days=30), end=datetime.now().date()):
        tags = entry_points.values()
        tags.append('osf')
        for tag in tags:
            yield tag, cls.get_product_count_history(tag, start=start, end=end)

    @classmethod
    def save_record(cls, result_dict, date=datetime.now().date()):
        total = result_dict.pop('total', None)
        for i in range(len(result_dict['tags'])):
            uc = cls(date=date,
                     tag=result_dict['tags'][i],
                     count=result_dict['count'][i],
                     percent=result_dict['percent'][i])
            uc.save()

    @classmethod
    def clear_table(cls):
        cls.objects.all().delete()


class DBMetrics(models.Model):
    class Meta:
        unique_together = (('date', 'name'),)
    date = models.DateField(auto_now_add=True)
    name = models.TextField()
    data = models.TextField()

    @classmethod
    def get_record(cls, date, names):
        try:
            results = cls.objects.filter(date=date,
                                         name__in=names)
            record = {}
            for result in results:
                record[result.name] = result.data
            return record
        except cls.DoesNotExist:
            return None

    @classmethod
    def save_record(cls, result_dict):
        for key, value in result_dict.items():
            metric = cls(name=key,
                         data=value)
            metric.save()
