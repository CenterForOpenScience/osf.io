from django.views.generic import ListView, TemplateView, View
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect

from osf.models.comment import Comment
from osf.models.user import OSFUser
from osf.models import SpamStatus

from osf.models.admin_log_entry import (
    update_admin_log,
    CONFIRM_HAM,
    CONFIRM_SPAM,
    UNFLAG_SPAM
)
from admin.comments.templatetags.comment_extras import reverse_comment_detail


class CommentList(PermissionRequiredMixin, ListView):
    """ Allow authorized admin user to see the things people have marked as spam
    """
    template_name = 'comments/spam_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = '-date_last_reported'
    permission_required = 'osf.view_spam'
    raise_exception = True

    def get_queryset(self):
        return Comment.objects.filter(
            spam_status=int(self.request.GET.get('status', '1'))
        ).exclude(
            reports={}
        ).exclude(
            reports=None
        )

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(queryset)
        paginator, page, queryset, is_paginated = self.paginate_queryset(queryset, page_size)
        return super().get_context_data(**{
            'spam': queryset,
            'page': page,
            'status': self.request.GET.get('status', '1'),
            'page_number': page.number
        }, **kwargs)


class UserCommentList(CommentList):
    """ Allow authorized admin user to see the comments a user has had
     marked spam
    """
    template_name = 'comments/user.html'

    def get_queryset(self):
        user = OSFUser.objects.get(guids___id=self.kwargs['user_guid'])
        return Comment.objects.filter(
            spam_status=int(self.request.GET.get('status', '1')),
            user=user
        ).exclude(
            reports={}
        ).exclude(
            reports=None
        ).order_by(
            self.ordering
        )

    def get_context_data(self, **kwargs):
        user = OSFUser.objects.get(guids___id=(self.kwargs.get('user_guid', None)))
        user.guid = user._id
        return super().get_context_data(**{'user': user}, **kwargs)


class CommentDetail(PermissionRequiredMixin, TemplateView):
    """ Allow authorized admin user to see details of reported spam.
    """
    template_name = 'comments/detail.html'
    permission_required = 'osf.view_spam'
    raise_exception = True

    def get_context_data(self, **kwargs):
        comment = Comment.objects.get(id=self.kwargs['comment_id'])
        user = comment.user
        user.guid = user._id
        return super().get_context_data(**{
            'comment': comment,
            'user': user,
            'page_number': self.request.GET.get('page', '1'),
            'status': self.request.GET.get('status', '1'),
            'SPAM_STATUS': SpamStatus,
        }, **kwargs)


class CommentSpamView(PermissionRequiredMixin, View):
    permission_required = 'osf.mark_spam'

    def post(self, request, comment_id, **kwargs):
        comment = Comment.objects.get(id=comment_id)

        action = request.POST['action']
        if action == 'spam':
            comment.confirm_spam(save=True)
            update_admin_log(
                user_id=request.user.id,
                object_id=comment._id,
                object_repr='Comment',
                message=f'Confirmed SPAM: {comment._id}',
                action_flag=CONFIRM_SPAM
            )

        if action == 'ham':
            comment.confirm_ham(save=True)
            update_admin_log(
                user_id=request.user.id,
                object_id=comment._id,
                object_repr='Comment',
                message=f'Confirmed HAM: {comment._id}',
                action_flag=CONFIRM_HAM
            )

        if action == 'unflag':
            comment.spam_status = None
            comment.save()
            update_admin_log(
                user_id=request.user.id,
                object_id=comment._id,
                object_repr='Comment',
                message=f'Confirmed Unflagged: {comment._id}',
                action_flag=UNFLAG_SPAM
            )

        return redirect(
            reverse_comment_detail(
                comment,
                page=self.request.GET.get('page', '1'),
                status=self.request.GET.get('status', '1')
            )
        )
