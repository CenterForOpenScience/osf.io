import time

from waterbutler import tasks
from waterbutler.server import utils
from waterbutler.server.handlers import core


class MoveHandler(core.BaseCrossProviderHandler):
    JSON_REQUIRED = True
    ACTION_MAP = {
        'POST': 'move'
    }

    @utils.coroutine
    def prepare(self):
        yield from super().prepare()

    @utils.coroutine
    def post(self):
        if not self.source_provider.can_intra_move(self.destination_provider, self.json['source']['path']):
            resp = yield from tasks.move.adelay({
                'nid': self.json['source']['nid'],
                'path': self.json['source']['path'],
                'provider': self.source_provider.serialized()
            }, {
                'nid': self.json['destination']['nid'],
                'path': self.json['destination']['path'],
                'provider': self.destination_provider.serialized()
            },
                self.callback_url,
                self.auth,
                rename=self.json.get('rename'),
                conflict=self.json.get('conflict', 'replace'),
                start_time=time.time()
            )

            metadata, created = yield from tasks.wait_on_celery(resp)

        else:
            metadata, created = (
                yield from tasks.backgrounded(
                    self.source_provider.move,
                    self.destination_provider,
                    self.json['source']['path'],
                    self.json['destination']['path'],
                    rename=self.json.get('rename'),
                    conflict=self.json.get('conflict', 'replace'),
                )
            )

            self._send_hook('move', metadata)

        if created:
            self.set_status(201)
        else:
            self.set_status(200)

        self.write(metadata)
