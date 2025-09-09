from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.contrib import messages
from osf.models import RegistrationProvider, OSFUser, NotificationType
from website.settings import DOMAIN


class AddAdminOrModerator(TemplateView):
    permission_required = 'osf.change_registrationprovider'
    template_name = 'registration_providers/edit_moderators.html'
    provider_class = RegistrationProvider
    url_namespace = 'registration_providers'
    raise_exception = True

    def get_context_data(self, **kwargs):
        provider = self.provider_class.objects.get(id=self.kwargs['provider_id'])
        context = super().get_context_data(**kwargs)
        context['provider'] = provider
        context['moderators'] = provider.get_group('moderator').user_set.all()
        context['admins'] = provider.get_group('admin').user_set.all()
        return context

    def post(self, request, *args, **kwargs):
        provider = self.provider_class.objects.get(id=self.kwargs['provider_id'])
        data = dict(request.POST)
        del data['csrfmiddlewaretoken']  # just to remove the key from the form dict

        target_user = OSFUser.load(data['add-moderators-form'][0])
        if target_user is None:
            messages.error(request, f'User for guid: {data["add-moderators-form"][0]} could not be found')
            return redirect(f'{self.url_namespace}:add_admin_or_moderator', provider_id=provider.id)

        if target_user.has_groups(provider.group_names):
            messages.error(request, f'User with guid: {data["add-moderators-form"][0]} is already a moderator or admin')
            return redirect(f'{self.url_namespace}:add_admin_or_moderator', provider_id=provider.id)

        context = {}
        context['notification_settings_url'] = f'{DOMAIN}reviews/preprints/{provider._id}/notifications'
        context['provider_name'] = provider.name
        context['provider__id'] = provider._id
        context['is_reviews_moderator_notification'] = True
        context['referrer_fullname'] = target_user.fullname
        context['user_fullname'] = target_user.fullname
        context['is_reviews_moderator_notification'] = True
        if 'admin' in data:
            provider.add_to_group(target_user, 'admin')
            target_type = 'admin'
            context['is_admin'] = True
        else:
            provider.add_to_group(target_user, 'moderator')
            target_type = 'moderator'
            context['is_admin'] = False

        notification_type = NotificationType.Type.PROVIDER_MODERATOR_ADDED
        notification_type.instance.emit(
            user=target_user,
            event_context=context,
        )

        messages.success(request, f'The following {target_type} was successfully added: {target_user.fullname} ({target_user.username})')

        return redirect(f'{self.url_namespace}:add_admin_or_moderator', provider_id=provider.id)


class RemoveAdminsAndModerators(TemplateView):
    permission_required = 'osf.change_registrationprovider'
    template_name = 'registration_providers/edit_moderators.html'
    provider_class = RegistrationProvider
    url_namespace = 'registration_providers'
    raise_exception = True

    def get_context_data(self, **kwargs):
        provider = self.provider_class.objects.get(id=self.kwargs['provider_id'])
        context = super().get_context_data(**kwargs)
        context['provider'] = provider
        context['moderators'] = provider.get_group('moderator').user_set.all()
        context['admins'] = provider.get_group('admin').user_set.all()
        return context

    def post(self, request, *args, **kwargs):
        provider = self.provider_class.objects.get(id=self.kwargs['provider_id'])
        data = dict(request.POST)
        del data['csrfmiddlewaretoken']  # just to remove the key from the form dict

        to_be_removed = list(data.keys())
        removed_admins = [admin.replace('Admin-', '') for admin in to_be_removed if 'Admin-' in admin]
        removed_moderators = [moderator.replace('Moderator-', '') for moderator in to_be_removed if 'Moderator-' in moderator]
        moderators = OSFUser.objects.filter(id__in=removed_moderators)
        admins = OSFUser.objects.filter(id__in=removed_admins)
        provider.get_group('moderator').user_set.remove(*moderators)
        provider.get_group('admin').user_set.remove(*admins)

        if moderators:
            moderator_names = ' ,'.join(moderators.values_list('fullname', flat=True))
            messages.success(request, f'The following moderators were successfully removed: {moderator_names}')

        if admins:
            admin_names = ' ,'.join(admins.values_list('fullname', flat=True))
            messages.success(request, f'The following admins were successfully removed: {admin_names}')

        return redirect(f'{self.url_namespace}:add_admin_or_moderator', provider_id=provider.id)
