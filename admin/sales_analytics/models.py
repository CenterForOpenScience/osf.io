from django.db import models


class DBMetrics(models.Model):
    date = models.DateField(auto_now_add=True)
    user_count = models.TextField()
    multi_product_metrics_yearly = models.TextField()
    multi_product_metrics_monthly = models.TextField()
    repeat_action_user_monthly = models.TextField()
