"""
Utilities to help run Django tests
* setup_view - replaces as_view
"""


def setup_view(view, request, *args, **kwargs):
    """Mimic as_view() returned callable, but returns view instance

    http://tech.novapost.fr/django-unit-test-your-views-en.html
    """
    view.request = request
    view.args = args
    view.kwargs = kwargs
    return view
