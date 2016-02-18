from django.shortcuts import render, redirect
from forms import ConferenceForm

# Create your views here.
def create_conference(request):
    if request.user.is_staff:
        if request.method == 'POST':
            form = ConferenceForm(request.POST)
            if form.is_valid():
                new_conference = form.save(commit=False)
                # Do stuff here if need be
                new_conference.save()
                return redirect('conferences:create_conference')
            else:
                print(form.errors)
                return redirect('conferences:create_conference')
        else:
            form = ConferenceForm()
            context = {'form': form}
            return render(request, 'conferences/create_conference.html', context)
    else:
        messages.error(request, 'You do not have permission to access that page.')
        return redirect('auth:login')