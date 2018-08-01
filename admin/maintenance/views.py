

import pytz
import datetime

from osf.models import MaintenanceState
import website.maintenance as maintenance
from admin.maintenance.forms import MaintenanceForm

from django.shortcuts import redirect
from django.forms.models import model_to_dict
from django.views.generic import DeleteView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin


class DeleteMaintenance(PermissionRequiredMixin, DeleteView):
    permission_required = 'osf.delete_maintenancestate'
    raise_exception = True
    template_name = 'maintenance/delete_maintenance.html'

    def get_object(self, queryset=None):
        return MaintenanceState.objects.first()

    def delete(self, request, *args, **kwargs):
        maintenance.unset_maintenance()
        return redirect('maintenance:display')


class MaintenanceDisplay(PermissionRequiredMixin, TemplateView):
    permission_required = 'osf.change_maintenancestate'
    raise_exception = True
    template_name = 'maintenance/display.html'

    def get_context_data(self, **kwargs):
        maintenance = MaintenanceState.objects.first()
        kwargs['form'] = MaintenanceForm()
        kwargs['current_alert'] = model_to_dict(maintenance) if maintenance else None
        return super(MaintenanceDisplay, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        data = request.POST

        start = convert_eastern_to_utc(data['start']).isoformat() if data.get('start') else None
        end = convert_eastern_to_utc(data['end']).isoformat() if data.get('end') else None

        maintenance.set_maintenance(data.get('message', ''), data['level'], start, end)
        return redirect('maintenance:display')


def convert_eastern_to_utc(date):
    local = pytz.timezone('US/Eastern')
    naive = datetime.datetime.strptime(date, '%Y/%m/%d %H:%M')
    local_dt = local.localize(naive, is_dst=None)
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt
