import os
import http
import json
import asyncio

from tornado import web

import waterbutler.core
from waterbutler import tasks
from waterbutler.core.streams import RequestStreamReader

from waterbutler.server import utils
from waterbutler.server import settings
from waterbutler.server.handlers import core
from waterbutler.server.identity import get_identity


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
        if not self.source_provider.can_intra_move(self.destination_provider):
            resp = yield from tasks.move.adelay({
                'args': self.json['source'],
                'provider': self.source_provider.serialized()
            }, {
                'args': self.json['destination'],
                'provider': self.destination_provider.serialized()
            },
                self.callback_url,
                self.auth
            )
            self.set_status(202)
            return

        metadata, created = (
            yield from tasks.backgrounded(
                self.source_provider.move,
                self.destination_provider,
                self.json['source'],
                self.json['destination']
            )
        )

        if created:
            self.set_status(201)
        else:
            self.set_status(200)

        self.write(metadata)

        self._send_hook('move', metadata)
