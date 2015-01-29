import tornado.web

import waterbutler

class StatusHandler(tornado.web.RequestHandler):

    def get(self):
        """List information about waterbutler status"""
        self.write({
            'status': 'up',
            'version': waterbutler.__version__
        })
