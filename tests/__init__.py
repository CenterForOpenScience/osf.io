# Types of input for renderers:


# * Dict
# * Redirect
# * HttpError (Rendered gets it as input)


# Returns: Flask-style tuple

# WebRendered handles redirects differently
# unpacks nested templates
# * nested templates should follow redirects
# * routing failures or other Exceptions should result in error message output

import unittest

from new_style import app

class OsfTestCase(unittest.TestCase):

    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()