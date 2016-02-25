from django.views.generic import FormView, ListView, DetailView

from .models import Institution, InstitutionForm


class InstitutionListView(ListView):
    pass


class InstitutionDetailView(DetailView):
    pass


class InstitutionFormView(FormView):
    pass
