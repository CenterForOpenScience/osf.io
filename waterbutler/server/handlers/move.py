import os
import http
import json
import asyncio

from tornado import web

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
        metadata, created = (
            yield from self.provider.move(
                self.dest_provider,
                self.arguments,
                self.json
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
