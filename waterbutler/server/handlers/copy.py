import asyncio

from waterbutler import tasks
from waterbutler.server import utils
from waterbutler.server import settings
from waterbutler.server.handlers import core


class CopyHandler(core.BaseCrossProviderHandler):
    JSON_REQUIRED = True
    ACTION_MAP = {
        'POST': 'copy'
    }

    @utils.coroutine
    def prepare(self):
        yield from super().prepare()

    @utils.coroutine
    def post(self):
        if not self.source_provider.can_intra_copy(self.destination_provider):
            resp = yield from tasks.copy.adelay({
                'path': self.json['source']['path'],
                'provider': self.source_provider.serialized()
            }, {
                'path': self.json['destination']['path'],
                'provider': self.destination_provider.serialized()
            },
                self.callback_url,
                self.auth,
                rename=self.json.get('rename'),
                conflict=self.json.get('conflict', 'replace'),
            )

            if not resp.ready():
                self.set_status(202)
                return
            metadata, created = resp.result
        else:
            metadata, created = (
                yield from tasks.backgrounded(
                    self.source_provider.copy,
                    self.destination_provider,
                    self.json['source']['path'],
                    self.json['destination']['path'],
                    rename=self.json.get('rename'),
                    conflict=self.json.get('conflict', 'replace'),
                )
            )

        if created:
            self.set_status(201)
        else:
            self.set_status(200)

        self.write(metadata)

        self._send_hook('copy', metadata)
