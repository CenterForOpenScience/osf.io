from django.db import models

class EmailTask(models.Model):
    TASK_STATUS = (
        ('PENDING', 'Pending'),
        ('NO_USER_FOUND', 'No User Found'),
        ('USER_DISABLED', 'User Disabled'),
        ('STARTED', 'Started'),
        ('SUCCESS', 'Success'),
        ('FAILURE', 'Failure'),
        ('RETRY', 'Retry'),
    )

    task_id = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey('osf.OSFUser', null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS, default='PENDING')
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f'{self.task_id} ({self.status})'
