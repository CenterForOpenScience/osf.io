from framework.flask import redirect


def redirect_activity_to_search(**kwargs):
    return redirect('/search/')
