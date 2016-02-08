from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required

from modularodm import Q
from website.project.model import Comment

from .serializers import serialize_comment


def get_spam_list():
    query = (
        Q('reports', 'ne', {}) &
        Q('reports', 'ne', None)
    )
    return Comment.find(query).sort('date_created')


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
    return render(request, 'spam/spam.html', context)


@login_required
def spam_detail(request, spam_id):
    context = {
        'comment': serialize_comment(Comment.load(spam_id)),
        'page_number': request.GET.get('page', 1),
    }
    return render(request, 'spam/comment.html', context)


@login_required
def email(request, spam_id):
    context = {
        'comment': serialize_comment(Comment.load(spam_id), full=True),
        'page_number': request.GET.get('page', 1),
    }
    return render(request, 'spam/email.html', context)
