import unittest

from new_style import app


class OsfTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()