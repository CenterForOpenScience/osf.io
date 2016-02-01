from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, FormView
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse

from modularodm import Q
from website.project.model import Comment

from .serializers import serialize_comment
from .forms import ConfirmForm


def get_spam_list(mark=Comment.FLAGGED):
    if mark not in (Comment.FLAGGED, Comment.SPAM, Comment.UNKNOWN, Comment.HAM):
        raise ValueError
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
        paginator = Paginator(get_spam_list(mark=int(spam_status)), 10)

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


class SpamDetail(FormView):
    form_class = ConfirmForm
    template_name = 'spam/comment.html'
    spam_id = None
    page = 1

    def __init__(self):
        self.item = None
        super(SpamDetail, self).__init__()

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        self.page = request.GET.get('page', 1)
        context['page_number'] = self.page
        context['form'] = self.get_form()
        return self.render_to_response(context)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        self.page = request.GET.get('page', 1)
        context['page_number'] = self.page
        return super(SpamDetail, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        self.spam_id = kwargs['spam_id']
        self.item = Comment.load(self.spam_id)
        kwargs = super(SpamDetail, self).get_context_data(**kwargs)
        kwargs['comment'] = serialize_comment(self.item)
        return kwargs

    def form_valid(self, form):
        if int(form.cleaned_data.get('confirm')) == Comment.SPAM:
            self.item.confirm_spam(save=True)
        else:
            self.item.confirm_ham(save=True)
        return super(SpamDetail, self).form_valid(form)

    @property
    def success_url(self):
        return reverse('spam:detail', kwargs={'spam_id': self.spam_id}) + '?page={}'.format(self.page)


@login_required
def email(request, spam_id):
    context = {
        'comment': serialize_comment(Comment.load(spam_id), full=True),
        'page_number': request.GET.get('page', 1),
    }
    return render(request, 'spam/email.html', context)
