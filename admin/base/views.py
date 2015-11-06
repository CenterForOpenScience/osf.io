from django.shortcuts import render


def root(request):

    return render(request, 'home.html')
    # return HttpResponse("Will probably need to put some front end Auth on this.")
