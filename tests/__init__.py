# Types of input for renderers:


# * Dict
# * Redirect
# * HttpError (Rendered gets it as input)


# Returns: Flask-style tuple

# WebRendered handles redirects differently
# unpacks nested templates
# * nested templates should follow redirects
# * routing failures or other Exceptions should result in error message output

from modular_templates.routing import *