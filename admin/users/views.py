from django.shortcuts import redirect
from django.views.defaults import page_not_found

from website.project.model import User
from website.mailchimp_utils import subscribe_on_confirm
from website.search.elastic_search import search
from website.search.util import build_query

from admin.base.views import GuidFormView, GuidView
from admin.users.templatetags.user_extras import reverse_user
from admin.users.forms import UserForm
from .serializers import serialize_user


def disable_user(request, guid):
    user = User.load(guid)
    user.disable_account()
    user.save()
    return redirect(reverse_user(guid))


def reactivate_user(request, guid):
    user = User.load(guid)
    user.date_disabled = None
    subscribe_on_confirm(user)
    user.save()


def remove_2_factor(request, guid):
    user = User.load(guid)
    try:
        user.delete_addon('twofactor')
    except AttributeError:
        page_not_found(request)
    return redirect(reverse_user(guid))


class UserFormView(GuidFormView):
    template_name = 'users/search.html'
    object_type = 'user'
    form_class = UserForm

    def form_valid(self, form):
        guid = form.cleaned_data.get('guid')
        name = form.cleaned_data.get('name')
        email = form.cleaned_data.get('email')
        if not name:
            name = '*'
        if not email:
            email = '*'
        search_string = '{} AND {} AND {}'.format(guid, name, email)
        query = build_query(search_string)


    @property
    def success_url(self):
        return reverse_user(self.guid)


class UserView(GuidView):
    template_name = 'users/user.html'
    context_object_name = 'user'

    def get_object(self, queryset=None):
        self.guid = self.kwargs.get('guid', None)
        return serialize_user(User.load(self.guid))
