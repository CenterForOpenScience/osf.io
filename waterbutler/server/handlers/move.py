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
        if not self.provider.can_intra_move(self.dest_provider):
            resp = yield from tasks.move({
                'args': self.arguments,
                'provider': self.provider.serialized()
            }, {
                'args': self.json,
                'provider': self.dest_provider.serialized()
            })
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

        # TODO copy/created?
        self._send_hook(
            'create' if created else 'update',
            metadata,
        )
