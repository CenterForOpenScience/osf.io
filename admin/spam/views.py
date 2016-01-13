import operator

from django.shortcuts import render, render_to_response
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.views.generic import FormView

from modularodm import Q
from website.project.model import Comment

from .serializers import serialize_comment
from .forms import EmailForm


class EmailFormView(FormView):

    form_class = EmailForm
    template_name = "spam/email.html"
    success_url = ''

    def get(self, request, *args, **kwargs):
        spam_id = kwargs.get('spam_id', None)
        try:
            spam = serialize_comment(Comment.load(spam_id))
        except:
            pass
        initial = {
            'name': spam['author'].fullname,
            'email': [(i, r) for i, r in enumerate(spam['author'].emails)],
            'subject': 'Reports of spam',
            'message': 'certainly <b> unfortunate </b>',  # TODO: <-
        }
        form = self.form_class(initial=initial)
        self.success_url = None  # TODO: <-
        context = {
            'comment': spam,
            'page_number': request.GET.get('page', 1),
            'form': form
        }
        return render(request, self.template_name, context)

    def form_valid(self, form):
        send_mail(
            subject=form.cleaned_data.get('subject').strip(),
            message=form.cleaned_data.get('message'),
            from_email='support@osf.io',
            recipient_list=[]  # TODO: <-
        )
        return super(EmailFormView, self).form_valid(form)


def get_spam_list():
    query = (
        Q('reports', 'ne', {}) &
        Q('reports', 'ne', None)
    )
    return sorted(
        Comment.find(query),
        key=operator.attrgetter('date_created')
    )


@login_required
def spam_list(request):
    paginator = Paginator(get_spam_list(), 10)

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
        'page_number': page_number,
    }
    return render_to_response('spam/spam.html', context)


@login_required
def spam_detail(request, spam_id):
    context = {
        'comment': serialize_comment(Comment.load(spam_id)),
        'page_number': request.GET.get('page', 1),
    }
    return render(request, 'spam/comment.html', context)
