from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator

from modularodm import Q
from website.project.model import Comment

from .serializers import serialize_comment


def get_spam_list(mark=1):
    query = (
        Q('reports', 'ne', {}) &
        Q('reports', 'ne', None) &
        Q('spam_status', 'eq', mark)
    )
    return Comment.find(query).sort('date_created')


class SpamList(TemplateView):
    template_name = 'spam/spam.html'

    @method_decorator(login_required)  # TODO: 1.9 upgrade to class decorator
    def get(self, request, *args, **kwargs):
        spam_status = request.GET.get('status', 1)
        paginator = Paginator(get_spam_list(mark=spam_status), 10)

        page_number = request.GET.get('page', 1)
        try:
            page = paginator.page(page_number)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)
        context = {
            'spam': map(serialize_comment, page),
            'page': page,
            'status': spam_status,
            'page_number': page_number,
        }
        return self.render_to_response(context)


class SpamDetail(TemplateView):
    template_name = 'spam/comment.html'
    spam_id = None

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['page_number'] = request.GET.get('page', 1)
        return self.render_to_response(context)

    @method_decorator(login_required)
    def post(self):
        pass

    def get_context_data(self, **kwargs):
        kwargs = super(SpamDetail, self).get_context_data(**kwargs)
        kwargs['comment'] = serialize_comment(Comment.load(kwargs['spam_id']))
        return kwargs


@login_required
def email(request, spam_id):
    context = {
        'comment': serialize_comment(Comment.load(spam_id), full=True),
        'page_number': request.GET.get('page', 1),
    }
    return render(request, 'spam/email.html', context)
