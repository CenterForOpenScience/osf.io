from django.http import HttpResponse

from .serializers import serialize_comments


def spam_list(request):
    return HttpResponse('This is a list of spam:{}'.format(' *** '.join(serialize_comments())))


def spam_detail(request, spam_id):
    return HttpResponse('Looking at spam {}'.format(spam_id))
