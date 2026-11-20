from django.apps import AppConfig as BaseAppConfig


class BaseAdminAppConfig(BaseAppConfig):
    name = 'admin.base'
    label = 'admin_base'

    def ready(self):
        from django.contrib import admin
        from dj_control_room_base.models import BasePanelPlaceholder
        from django_celery_beat.admin import PeriodicTaskAdmin
        from django_celery_beat.models import (
            ClockedSchedule,
            CrontabSchedule,
            IntervalSchedule,
            PeriodicTask,
            SolarSchedule,
        )

        # dj_control_room_base is installed only for dj_celery_panel's templates/static; hide its demo panel
        admin.site.unregister(BasePanelPlaceholder)

        # Schedules are managed through CeleryConfig.beat_schedule, so only the periodic task list is exposed
        admin.site.unregister((ClockedSchedule, CrontabSchedule, IntervalSchedule, SolarSchedule))

        # Read-only Periodic Tasks admin panel: list and view pages only, no actions, add, change or delete
        class ReadOnlyPeriodicTaskAdmin(PeriodicTaskAdmin):
            actions = None

            def has_add_permission(self, request):
                return False

            def has_change_permission(self, request, obj=None):
                return False

            def has_delete_permission(self, request, obj=None):
                return False

        admin.site.unregister(PeriodicTask)
        admin.site.register(PeriodicTask, ReadOnlyPeriodicTaskAdmin)
