# -*- coding: utf-8 -*-

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic import UpdateView, TemplateView, FormView

from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_announcement.forms import PreviewForm, SendForm, SettingsForm

from osf.models.rdm_announcement import RdmAnnouncementOption, RdmFcmDevice
from osf.models.user import OSFUser
from django.core.mail import EmailMessage
from website.settings import SUPPORT_EMAIL
from admin.base.settings import FCM_SETTINGS
from admin.base.settings import EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS  # noqa
from redminelib import Redmine
from pyfcm import FCMNotification
import facebook
from urlparse import urlparse
import tweepy

class RdmAnnouncementPermissionMixin(RdmPermissionMixin):
    @property
    def has_auth(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False
        # allowed by superuser, or institution administrator
        if self.is_super_admin or self.is_admin:
            return True
        return False

class IndexView(RdmAnnouncementPermissionMixin, UserPassesTestMixin, TemplateView):
    template_name = 'rdm_announcement/index.html'
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        return self.has_auth

    def get_context_data(self, **kwargs):
        ctx = super(IndexView, self).get_context_data(**kwargs)
        ctx['form'] = PreviewForm
        return ctx

    def post(self, request, *args, **kwargs):
        form = PreviewForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if self.option_check(data):
                return render(request, 'rdm_announcement/send.html', {'data': data, 'form': form})
            else:
                msg = 'Please set ' + data['announcement_type'][5:-1] + ' Options first'
            return render(request, 'rdm_announcement/index.html', {'msg': msg, 'form': form})
        else:
            error = form.errors.as_data()
            msg = error.values()[0][0].messages[0]
            return render(request, 'rdm_announcement/index.html', {'msg': msg, 'form': form})

    # RDM Announcements - Options Check
    def option_check(self, data):
        is_ok = True
        login_user_id = self.request.user.id
        announcement_type = data['announcement_type']
        if RdmAnnouncementOption.objects.filter(user_id=login_user_id).exists():
            option = RdmAnnouncementOption.objects.get(user_id=login_user_id)
            if announcement_type != 'SNS (Twitter)' and announcement_type != 'SNS (Facebook)':
                return is_ok
            elif announcement_type == 'SNS (Facebook)':
                option_names = ['facebook_api_key', 'facebook_api_secret', 'facebook_access_token']
            else:
                option_names = ['twitter_api_key', 'twitter_api_secret', 'twitter_access_token',
                                'twitter_access_token_secret']
            for name in option_names:
                if not getattr(option, name):
                    is_ok = False
        else:
            if announcement_type == 'SNS (Twitter)' or announcement_type == 'SNS (Facebook)':
                is_ok = False
        return is_ok

class SettingsView(RdmAnnouncementPermissionMixin, UserPassesTestMixin, TemplateView):
    form_class = SettingsForm
    model = SettingsForm.Meta.model
    template_name = 'rdm_announcement/settings.html'
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        return self.has_auth

    def get_context_data(self, **kwargs):
        login_user_id = self.request.user.id
        ctx = super(SettingsView, self).get_context_data(**kwargs)
        ctx['form'] = SettingsForm
        if RdmAnnouncementOption.objects.filter(user_id=login_user_id).exists():
            ctx['form'] = SettingsForm(instance=RdmAnnouncementOption.objects.get(user_id=login_user_id))
        else:
            create_option_from_other = self.get_exist_option_set()
            if create_option_from_other == 'True':
                ctx['form'] = SettingsForm(instance=RdmAnnouncementOption.objects.get(user_id=login_user_id))

        if RdmAnnouncementOption.objects.filter(user_id=login_user_id).exists():
            ctx['form'] = SettingsForm(instance=RdmAnnouncementOption.objects.get(user_id=login_user_id))
        return ctx

    def get_exist_option_set(self):
        now_user = self.request.user
        login_user_id = self.request.user.id
        result = 'False'
        copy_option_id = ''
        if self.is_super_admin:
            all_superuser_id_list = list(OSFUser.objects.filter(is_superuser=True).values_list('pk', flat=True))
            superuser_option_id_list = list(RdmAnnouncementOption.objects.filter(user_id__in=all_superuser_id_list).values_list('pk', flat=True))
            if len(superuser_option_id_list) > 0:
                copy_option_id = superuser_option_id_list[0]
        elif self.is_admin:
            now_institutions_id = list(now_user.affiliated_institutions.all().values_list('pk', flat=True))
            all_institution_users_id = list(OSFUser.objects.filter(affiliated_institutions__in=now_institutions_id).distinct().values_list('pk', flat=True))
            institution_option_id_list = list(RdmAnnouncementOption.objects.filter(user_id__in=all_institution_users_id).values_list('pk', flat=True))
            if len(institution_option_id_list) > 0:
                copy_option_id = institution_option_id_list[0]
        if copy_option_id != '':
            new_option = RdmAnnouncementOption.objects.get(pk=copy_option_id)
            new_option.pk = None
            new_option.user_id = login_user_id
            new_option.save()
            result = 'True'
        return result

class SettingsUpdateView(RdmAnnouncementPermissionMixin, UserPassesTestMixin, UpdateView):
    form_class = SettingsForm
    model = SettingsForm.Meta.model
    template_name = 'rdm_announcement/settings.html'
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        return self.has_auth

    def get_object(self, queryset=None):
        login_user_id = self.request.user.id
        return RdmAnnouncementOption.objects.get(user_id=login_user_id)

    def post(self, request, *args, **kwargs):
        login_user_id = self.request.user.id
        if RdmAnnouncementOption.objects.filter(user_id=login_user_id).exists():
            form = SettingsForm(request.POST, instance=RdmAnnouncementOption.objects.get(user_id=login_user_id))
        else:
            form = SettingsForm(request.POST)
        if form.is_valid():
            temp = form.save(commit=False)
            temp.user_id = login_user_id
            temp.save()
            self.update_exist_option(form)

        return redirect(reverse_lazy('announcement:index'))

    def update_exist_option(self, form):
        now_user = self.request.user
        login_user_id = self.request.user.id
        data = form.cleaned_data
        all_superuser_id_list = []
        if self.is_super_admin:
            all_superuser_id_list = list(OSFUser.objects.filter(is_superuser=True).values_list('pk', flat=True))
            all_superuser_id_list.remove(login_user_id)
            RdmAnnouncementOption.objects.filter(user_id__in=all_superuser_id_list).update(**data)
        elif self.is_admin:
            now_institutions_id = list(now_user.affiliated_institutions.all().values_list('pk', flat=True))
            all_institution_users_id = list(OSFUser.objects.filter(affiliated_institutions__in=now_institutions_id).distinct().values_list('pk', flat=True))
            all_institution_users_id.remove(login_user_id)
            RdmAnnouncementOption.objects.filter(user_id__in=all_superuser_id_list).update(**data)

    def get(self, request, *args, **kwargs):
        return redirect(reverse_lazy('announcement:settings'))

class SendView(RdmAnnouncementPermissionMixin, UserPassesTestMixin, FormView):
    form_class = SendForm
    model = SendForm.Meta.model
    template_name = 'rdm_announcement/send.html'
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        return self.has_auth

    def post(self, request, *args, **kwargs):
        login_user_id = self.request.user.id
        form = SendForm(request.POST)
        if form.is_valid():
            ret = self.send(form)
            data = form.cleaned_data
            if ret['is_success']:
                temp = form.save(commit=False)
                temp.user_id = login_user_id
                temp.save()
                msg = 'Send successfully!'
            else:
                msg = ret['error']
        else:
            error = form.errors.as_data()
            msg = error.values()[0][0].messages[0]
            data = form.cleaned_data
        return render(request, 'rdm_announcement/send.html', {'msg': msg, 'data': data})

    def send(self, form):
        data = form.cleaned_data
        announcement_type = data['announcement_type']
        login_user_id = self.request.user.id
        if RdmAnnouncementOption.objects.filter(user_id=login_user_id).exists():
            option = RdmAnnouncementOption.objects.get(user_id=login_user_id)
        else:
            option = RdmAnnouncementOption.objects.create()
        if announcement_type == 'Email':
            ret = self.send_email(data)
        elif announcement_type == 'SNS (Twitter)':
            ret = self.send_twitter(data, option)
        elif announcement_type == 'SNS (Facebook)':
            ret = self.send_facebook(data, option)
        else:
            ret = self.push_notification(data)
        if ret['is_success'] and getattr(option, 'redmine_api_url') and getattr(option, 'redmine_api_key'):
            if option.redmine_api_url and option.redmine_api_key:
                ret = self.send_redmine(data, option)
        return ret
    # Email
    def send_email(self, data):
        ret = {'is_success': True, 'error': ''}
        now_user = self.request.user
        to_list = []
        if self.is_super_admin:
            all_users = OSFUser.objects.all()
            for user in all_users:
                if user.is_active and user.is_registered:
                    to_list.append(user.username)
        elif self.is_admin:
            now_institutions_id = list(now_user.affiliated_institutions.all().values_list('pk', flat=True))
            qs = OSFUser.objects.filter(affiliated_institutions__in=now_institutions_id).distinct().values_list('username', flat=True)
            to_list = list(qs)
        else:
            ret['is_success'] = False
            return ret
        try:
            email = EmailMessage(
                subject=data['title'],
                body=data['body'],
                from_email=SUPPORT_EMAIL or now_user.username,
                to=[SUPPORT_EMAIL or now_user.username],
                bcc=to_list
            )
            email.send(fail_silently=False)
        except Exception as e:
            ret['is_success'] = False
            ret['error'] = 'Email error: ' + str(e)
        finally:
            return ret

    # SNS (Twitter)
    def send_twitter(self, data, option):
        ret = {'is_success': True, 'error': ''}
        try:
            auth = tweepy.OAuthHandler(getattr(option, 'twitter_api_key'), getattr(option, 'twitter_api_secret'),)
            auth.set_access_token(getattr(option, 'twitter_access_token'), getattr(option, 'twitter_access_token_secret'))
            api = tweepy.API(auth)
            api.update_status(data['body'])
        except Exception as e:
            ret['is_success'] = False
            ret['error'] = 'Twitter error: ' + e.message[0]['message']
        finally:
            return ret

    # SNS (Facebook)
    def send_facebook(self, data, option):
        ret = {'is_success': True, 'error': ''}
        try:
            expired_token = getattr(option, 'facebook_access_token')
            user_graph = facebook.GraphAPI(expired_token, version='2.11')
            debug_access_token = facebook.GraphAPI().debug_access_token(expired_token, getattr(option, 'facebook_api_key'), getattr(option, 'facebook_api_secret'))
            is_valid = debug_access_token['data']['is_valid']
            if is_valid:
                user_graph.put_object(parent_object='me', connection_name='feed',
                                    message=data['body'])
            else:
                ret['is_success'] = False
                ret['error'] = 'Facebook error: Please reset access_token'
        except Exception as e:
            ret['is_success'] = False
            ret['error'] = 'Facebook error: ' + str(e)
        finally:
            return ret

    # Push notification
    def push_notification(self, data):
        ret = {'is_success': True, 'error': ''}
        now_user = self.request.user
        to_list = []
        if self.is_super_admin:
            all_users_id = list(OSFUser.objects.all().values_list('pk', flat=True))
            all_tokens = RdmFcmDevice.objects.filter(user_id__in=all_users_id).distinct().values_list(
                'device_token', flat=True)
            to_list = list(all_tokens)
        elif self.is_admin:
            now_institutions_id = list(now_user.affiliated_institutions.all().values_list('pk', flat=True))
            all_institution_users_id = list(OSFUser.objects.filter(affiliated_institutions__in=now_institutions_id).distinct().values_list(
                'pk', flat=True))
            all_institution_tokens = RdmFcmDevice.objects.filter(user_id__in=all_institution_users_id).distinct().values_list(
                'device_token', flat=True)
            to_list = list(all_institution_tokens)
        else:
            ret['is_success'] = False
            return ret
        try:
            api_key = FCM_SETTINGS.get('FCM_SERVER_KEY')
            FCMNotification(api_key=api_key)
            push_service = FCMNotification(api_key=api_key)
            registration_ids = to_list
            message_title = data['title']
            message_body = data['body']
            push_service.notify_multiple_devices(registration_ids=registration_ids, message_title=message_title,
                                                 message_body=message_body)
        except Exception as e:
            ret['is_success'] = False
            ret['error'] = 'Push notification error: ' + str(e)
        finally:
            return ret

    # Redmine
    def send_redmine(self, data, option):
        ret = {'is_success': True, 'error': ''}
        try:
            api_url = getattr(option, 'redmine_api_url')
            api_key = getattr(option, 'redmine_api_key')
            url_info = urlparse(api_url)
            redmine_url = url_info.scheme + '://' + url_info.netloc
            project_identifier = url_info.path.split('/')[2]
            redmine = Redmine(redmine_url, key=api_key, raise_attr_exception=('Project', 'Issue'))
            issue = redmine.issue.new()
            all_status_id = list(redmine.issue_status.all().values_list('id', flat=True))
            all_priority_id = list(redmine.enumeration.filter(resource='issue_priorities').values_list('id', flat=True))
            issue.project_id = project_identifier
            issue.subject = '[{}] {}'.format(data['announcement_type'], data['title'])
            issue.description = data['body']
            issue.status_id = all_status_id[0]
            issue.priority_id = all_priority_id[0]
            issue.save()
        except Exception as e:
            ret['is_success'] = False
            ret['error'] = 'Redmine error: ' + str(e)
        finally:
            return ret

    def get(self, request, *args, **kwargs):
        return redirect(reverse_lazy('announcement:index'))
