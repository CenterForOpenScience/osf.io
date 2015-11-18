from django.shortcuts import render, render_to_response
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .serializers import serialize_comments, retrieve_comment


def spam_list(request):
    comment_list = serialize_comments()
    paginator = Paginator(comment_list, 10)

    page = request.GET.get('page', 1)
    try:
        comments = paginator.page(page)
    except PageNotAnInteger:
        comments = paginator.page(1)
    except EmptyPage:
        comments = paginator.page(paginator.num_pages)
    return render_to_response('spam/spam.html', {'comments': comments})


def spam_detail(request, spam_id):
    comment = retrieve_comment(spam_id)
    context = {'comment': comment}
    return render(request, 'spam/comment.html', context)


def spam_sub_list(request, spam_ids):
    comments = None
    context = {'comments': comments}
    # should test for impossibilities such as many users. Return error page.
    return render(request, 'spam/sub_list.html', context)


def email(request, spam_id):
    comment = retrieve_comment(spam_id, full_user=True)
    context = {'comment': comment}
    return render(request, 'spam/email.html', context)
