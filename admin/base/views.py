from django.shortcuts import render


#def root(request):
#   return HttpResponse("Will probably need to put some front end Auth on this.")

@login_required
def home(request):
    context = {'user': request.user}
    return render(request, 'home.html', context)
