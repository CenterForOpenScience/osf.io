from django.core.paginator import Paginator
from django.db.models import F, Prefetch, Q
from django.urls import reverse, reverse_lazy
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView, View
from django.views.generic.edit import FormView, UpdateView, CreateView
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth import login, REDIRECT_FIELD_NAME, authenticate, logout

from osf.models.user import OSFUser
from osf.models import AdminProfile
from admin.base.utils import login_not_required
from admin.common_auth.forms import LoginForm, UserRegistrationForm, DeskUserForm, TwoFactorForm, get_admin_app_groups


class LoginView(FormView):
    form_class = LoginForm
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'login.html'

    @method_decorator(login_not_required)
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        if self.request.method == 'POST':
            if 'code' in self.request.POST:
                return TwoFactorForm

        return LoginForm

    def post(self, request, *args, **kwargs):
        form = self.get_context_data()['form']
        if isinstance(form, LoginForm):
            error_message = 'Email and/or Password incorrect. Please try again.'
        else:
            error_message = 'Invalid two-factor code. Please try again.'
            if 'guid' not in form.data:
                error_message = 'Email and/or Password incorrect. Please try again.'

        if not form.is_valid():
            messages.error(self.request, error_message)
            return redirect('auth:login')

        email = form.cleaned_data.get('email', '').strip()
        password = form.cleaned_data.get('password', '').strip()
        guid = form.cleaned_data.get('guid', '')
        if isinstance(form, LoginForm):
            user = authenticate(username=email, password=password)
        else:
            user = OSFUser.load(guid)

        if not user:
            messages.error(request, error_message)
            return redirect('auth:login')

        # login and two-factor auth is not possible without having two-factor auth enabled
        two_factor_settings = user.enabled_two_factor_settings
        if not two_factor_settings:
            messages.error(
                request,
                'Two-factor authentication must be enabled.'
            )
            return redirect('auth:login')

        # to not lose user after login request, we save its guid
        # and use HiddenInput to not display it
        if isinstance(form, LoginForm):
            self.form_class = TwoFactorForm
            return render(
                request,
                'two_factor.html',
                {
                    'form': self.form_class(
                        initial={
                            'guid': str(user._id),
                        }
                    )
                }
            )

        # two-factor section
        is_valid_code = two_factor_settings.verify_code(form.cleaned_data.get('code'))
        if not is_valid_code:
            messages.error(
                self.request,
                'Invalid two-factor code. Please try again.'
            )
            self.form_class = TwoFactorForm
            return render(
                request,
                'two_factor.html',
                {
                    'form': self.form_class(
                        initial={
                            'guid': str(user._id)
                        }
                    )
                }
            )

        # during 2FA step we don't authenticate user via authenticate(),
        # so need to specify backend to set all appropriate attributes to the user correctly
        user.backend = 'api.base.authentication.backends.ODMBackend'
        login(self.request, user)
        return super().post(request, *args, **kwargs)

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
    permission_required = 'osf.admin_user_management'
    raise_exception = True

    def form_valid(self, form):
        osf_id = form.cleaned_data.get('osf_id')
        osf_user = OSFUser.load(osf_id)

        if not osf_user:
            raise Http404(f'OSF user with id "{osf_id}" not found. Please double check.')

        osf_user.is_staff = True
        osf_user.save()

        # create AdminProfile for this new user
        profile, created = AdminProfile.objects.get_or_create(user=osf_user)
        osf_user.groups.add(*form.cleaned_data.get('group_perms'))
        osf_user.save()

        if created:
            messages.success(self.request, f'Registration successful for OSF User {osf_user.username}!')
        else:
            messages.success(self.request, f'Permissions update successful for OSF User {osf_user.username}!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('auth:register')

    def get_initial(self):
        initial = super().get_initial()
        initial['osf_id'] = self.request.GET.get('id')
        return initial


class AdminUserAudit(PermissionRequiredMixin, TemplateView):
    """Lists every staff user and superuser, with their admin groups, so their admin access can be reviewed"""
    template_name = 'admin_audit.html'
    permission_required = 'osf.admin_user_management'
    raise_exception = True
    paginate_by = 25

    def get_context_data(self, **kwargs):
        admin_users = OSFUser.objects.filter(
            Q(is_staff=True) | Q(is_superuser=True)
        ).annotate(
            guid=F('guids___id')
        ).prefetch_related(
            Prefetch('groups', queryset=get_admin_app_groups(), to_attr='admin_app_groups')
        ).order_by('-is_superuser', 'username')
        page = Paginator(admin_users, self.paginate_by).get_page(self.request.GET.get('page'))
        return super().get_context_data(page=page, admin_users=page.object_list, **kwargs)


class AdminUserAuditChange(PermissionRequiredMixin, View):
    """Base for the admin audit page actions: changes one user, then goes back to the audit page"""
    permission_required = 'osf.admin_user_management'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(OSFUser, guids___id=kwargs['guid'])
        if user == request.user:
            messages.error(request, 'You cannot change your own staff or superuser status.')
        else:
            self.change(user)
        return redirect(self.get_success_url())

    def change(self, user):
        raise NotImplementedError

    def get_success_url(self):
        url = reverse('auth:admin_audit')
        page = self.request.POST.get('page', '')
        return f'{url}?page={page}' if page.isdigit() else url


class AdminUserStaffChange(AdminUserAuditChange):
    """Sets is_staff to the posted value, which grants or revokes access to the admin app"""

    def change(self, user):
        user.is_staff = self.request.POST.get('is_staff') == 'true'
        user.save()
        status = 'granted' if user.is_staff else 'revoked'
        messages.success(self.request, f'Staff status {status} for {user.username}.')


class AdminUserSuperuserRevoke(AdminUserAuditChange):
    """Takes away superuser status"""

    def change(self, user):
        user.is_superuser = False
        user.save()
        messages.success(self.request, f'Superuser status revoked for {user.username}.')


class DeskUserCreateFormView(PermissionRequiredMixin, CreateView):
    form_class = DeskUserForm
    template_name = 'desk/settings.html'
    success_url = reverse_lazy('auth:desk')
    permission_required = 'osf.view_desk'
    raise_exception = True

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class DeskUserUpdateFormView(PermissionRequiredMixin, UpdateView):
    form_class = DeskUserForm
    template_name = 'desk/settings.html'
    success_url = reverse_lazy('auth:desk')
    permission_required = 'osf.view_desk'
    raise_exception = True

    def get_object(self, queryset=None):
        return self.request.user.admin_profile
