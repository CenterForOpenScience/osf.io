from django.views.generic import ListView

from .utils import DeskClient


class DeskCaseList(ListView):
    template_name = 'desk/cases.html'
    ordering = 'updated_at'

    def __init__(self):
        self.desk = None
        super(DeskCaseList, self).__init__()

    def get(self, request, *args, **kwargs):
        self.desk = DeskClient(sitename=None, username=None, password=None)
        super(DeskCaseList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        pass
