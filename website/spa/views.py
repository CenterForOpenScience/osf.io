from framework.auth.decorators import must_be_logged_in


@must_be_logged_in
def index(*args, **kwargs):
    return {}
