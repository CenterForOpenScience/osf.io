from __future__ import absolute_import, unicode_literals

from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView, UpdateView, CreateView
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth import login, REDIRECT_FIELD_NAME, authenticate, logout

from osf.models.user import OSFUser
from osf.models import AdminProfile
from admin.common_auth.forms import LoginForm, UserRegistrationForm, DeskUserForm

from osf.models.institution import Institution
from framework.auth import get_or_create_user
from framework.auth.core import get_user
from admin.base.settings import SHIB_EPPN_SCOPING_SEPARATOR

from django.views.generic.base import RedirectView
from api.institutions.authentication import login_by_eppn
import logging
logger = logging.getLogger(__name__)

import logging
logger = logging.getLogger(__name__)

class LoginView(FormView):
    form_class = LoginForm
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'login.html'

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(LoginView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = authenticate(
            username=form.cleaned_data.get('email').strip(),
            password=form.cleaned_data.get('password').strip()
        )
        if user is not None:
            login(self.request, user)
        else:
            messages.error(
                self.request,
                'Email and/or Password incorrect. Please try again.'
            )
            return redirect('auth:login')
        return super(LoginView, self).form_valid(form)

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name, '')
        if not redirect_to or redirect_to == '/':
            redirect_to = reverse('home')
        return redirect_to

class ShibLoginView(RedirectView):
    form_class = LoginForm
    redirect_field_name = REDIRECT_FIELD_NAME

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):

        eppn = request.environ['HTTP_AUTH_EPPN']
        seps = eppn.split(SHIB_EPPN_SCOPING_SEPARATOR)[-1]
        institution = Institution.objects.filter(domains__contains=[str(seps)]).first()
        if not institution:
            return redirect('auth:login')

        if not eppn:
            message = 'login failed: eppn required'
            logging.info(message)
            messages.error(self.request, message)
            return redirect('auth:login')
        eppn_user = get_user(eppn=eppn)
        if eppn_user:
            if 'GakuninRDMAdmin' in request.environ['HTTP_AUTH_ENTITLEMENT']:
                # login success
                # code is below this if/else tree
                eppn_user.is_staff = True
                #eppn_user.is_superuser = True
                eppn_user.save()
            else:
                # login failure occurs and the screen transits to the error screen
                # not sure about this code
                eppn_user.is_staff = False
                # eppn_user.is_superuser = False
                eppn_user.save()
                message = 'login failed: not staff or superuser'
                logging.info(message)
                messages.error(self.request, message)
                return redirect('auth:login')
        else:
            if 'GakuninRDMAdmin' not in request.environ['HTTP_AUTH_ENTITLEMENT']:
                message = 'login failed: no user with matching eppn'
                messages.error(self.request, message)
                return redirect('auth:login')
            else:
                new_user, created = get_or_create_user(request.environ['HTTP_AUTH_DISPLAYNAME'] or 'NO NAME', eppn, reset_password=False)
                USE_EPPN = login_by_eppn()
                if USE_EPPN:
                    new_user.eppn = eppn
                    mew_user.have_email = False
                    #user.unclaimed_records = {}
                    new_username = eppn
                else:
                    new_user.eppn = None
                    new_user.have_email = True
                new_user.is_staff = True
                new_user.eppn = eppn
                new_user.have_email = False
                new_user.save()
                new_user.affiliated_institutions.add(institution)
                eppn_user = new_user

        login(request, eppn_user, backend='api.base.authentication.backends.ODMBackend')

        # Transit to the administrator's home screen
        return redirect(self.get_success_url())

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name, '')
        if not redirect_to or redirect_to == '/':
            redirect_to = reverse('home')
        return redirect_to

def logout_user(request):
    logout(request)
    return redirect('auth:login')


class RegisterUser(PermissionRequiredMixin, FormView):
    form_class = UserRegistrationForm
    template_name = 'register.html'
    permission_required = 'osf.change_user'
    raise_exception = True

    def form_valid(self, form):
        osf_id = form.cleaned_data.get('osf_id')
        osf_user = OSFUser.load(osf_id)

        if not osf_user:
            raise Http404('OSF user with id "{}" not found. Please double check.'.format(osf_id))

        osf_user.is_staff = True
        osf_user.save()

        # create AdminProfile for this new user
        profile, created = AdminProfile.objects.get_or_create(user=osf_user)

        osf_user.groups.clear()
        prereg_admin_group = Group.objects.get(name='prereg_admin')
        for group in form.cleaned_data.get('group_perms'):
            osf_user.groups.add(group)
            if group == prereg_admin_group:
                administer_permission = Permission.objects.get(codename='administer_prereg')
                osf_user.user_permissions.add(administer_permission)

        osf_user.save()

        if created:
            messages.success(self.request, 'Registration successful for OSF User {}!'.format(osf_user.username))
        else:
            messages.success(self.request, 'Permissions update successful for OSF User {}!'.format(osf_user.username))
        return super(RegisterUser, self).form_valid(form)

    def get_success_url(self):
        return reverse('auth:register')

    def get_initial(self):
        initial = super(RegisterUser, self).get_initial()
        initial['osf_id'] = self.request.GET.get('id')
        return initial

class DeskUserCreateFormView(PermissionRequiredMixin, CreateView):
    form_class = DeskUserForm
    template_name = 'desk/settings.html'
    success_url = reverse_lazy('auth:desk')
    permission_required = 'osf.view_desk'
    raise_exception = True

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(DeskUserCreateFormView, self).form_valid(form)


class DeskUserUpdateFormView(PermissionRequiredMixin, UpdateView):
    form_class = DeskUserForm
    template_name = 'desk/settings.html'
    success_url = reverse_lazy('auth:desk')
    permission_required = 'osf.view_desk'
    raise_exception = True

    def get_object(self, queryset=None):
        return self.request.user.admin_profile
