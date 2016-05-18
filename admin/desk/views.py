from django.shortcuts import render
from django.views.generic import ListView, DetailView, FormView

from website.project.model import User

from admin.base.utils import OSFAdmin
from admin.desk.utils import DeskClient, DeskError


class DeskCaseList(OSFAdmin, ListView):
    template_name = 'desk/cases_modal.html'
    ordering = 'updated_at'
    context_object_name = 'cases'
    paginate_by = 100
    paginate_orphans = 5

    def get_queryset(self):
        customer_id = self.kwargs.get('user_id', None)
        customer = User.load(customer_id)
        email = customer.emails[0]
        desk_user = self.request.user
        desk = DeskClient(username=desk_user.desk_email,
                          password=desk_user.desk_password)
        params = {
            'status': 'new,open,closed',
            'email': email,
        }
        queryset = desk.cases(params)
        return queryset

    def get_template_names(self):
        if self.request.GET.get('modal') is not None:
            return self.template_name
        return 'desk/cases.html'

    def get_context_data(self, **kwargs):
        kwargs.setdefault('user_id', self.kwargs.get('user_id'))
        kwargs.setdefault('desk_link', 'https://{}.desk.com/web/agent/case/'.format(DeskClient.SITE_NAME))
        return super(DeskCaseList, self).get_context_data(**kwargs)


class DeskCaseFormView(OSFAdmin, FormView):
    pass


class DeskCustomer(OSFAdmin, DetailView):
    template_name = 'desk/customer.html'
    context_object_name = 'customer'

    def get(self, request, *args, **kwargs):
        try:
            return super(DeskCustomer, self).get(request, *args, **kwargs)
        except (AttributeError, DeskError) as e:
            return render(request, 'desk/user_not_found.html',
                          context={'email': e.status})

    def get_object(self, queryset=None):
        customer_id = self.kwargs.get('user_id', None)
        customer = User.load(customer_id)
        email = customer.emails[0]
        desk_user = self.request.user
        desk = DeskClient(username=desk_user.desk_email,
                          password=desk_user.desk_password)
        params = {'email': email}
        customer = desk.find_customer(params)
        if customer == {}:
            raise DeskError(email)
        return customer


class DeskCustomerFormView(OSFAdmin, FormView):
    pass
