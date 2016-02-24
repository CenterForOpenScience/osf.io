from django.views.generic import ListView

from .utils import DeskClient


class DeskCaseList(ListView):
    template_name = 'desk/cases.html'
    ordering = 'updated_at'
    context_object_name = 'cases'
    paginate_by = 10
    paginate_orphans = 1

    def __init__(self):
        self.desk = None
        super(DeskCaseList, self).__init__()

    def get(self, request, *args, **kwargs):
        user = request.user
        self.desk = DeskClient(username=user.desk_email,
                               password=user.desk_password)
        return super(DeskCaseList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        params = {'status': 'new,open,closed'}
        queryset = self.desk.cases(params)
        return queryset
