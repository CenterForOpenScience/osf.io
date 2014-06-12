import re

# produces a human-helpful debug message if you try to overwrite an existing endpoint function
def flask_endpoint_overwrite(error):
    m = re.match(
        'View function mapping is overwriting an existing endpoint function: (.*)__(.*)',
        error.message)
    if not m:
        return None

    clobbered_renderer = m.group(1)
    clobbered_function = m.group(2)

    human_message = ' '.join(["You're trying to overwrite an existing",
                    "Flask endpoint with a renderer named `{}`".format(clobbered_renderer),
                    "and a view function named `{}`.".format(clobbered_function),
                    "You can't do that. Rename your view function or add a suffix."])
    return human_message
