from django.http import HttpResponse


def spam_list(request):
    return HttpResponse('This is a list of spam')


def spam_detail(request, spam_id):
    return HttpResponse('Looking at spam {}'.format(spam_id))
