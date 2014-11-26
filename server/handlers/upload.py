# encoding: utf-8

from tornado import gen
from tornado import web

def int_or_none(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


@web.stream_request_body
class UploadHandler(web.RequestHandler):

    def setup(self):
        self.payload = None
        # self.signature = None
        # self.provider = None
        self.content_length = int_or_none(
            self.request.headers.get('Content-Length')
        )
        self.errors = []

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

    # def options(self):
    #     self.set_header('Access-Control-Allow-Headers', ', '.join(CORS_ACCEPT_HEADERS))
    #     self.set_header('Access-Control-Allow-Methods', 'PUT'),
    #     self.set_status(httplib.NO_CONTENT)

    @gen.coroutine
    def prepare(self):
        """Verify signed URL and notify metadata application of upload start.
        If either check fails, cancel upload.
        """
        self.setup()
        # self.payload, self.signature = verify_upload(self.request)
        # self.provider = StorageProvider.get('osfstorageprovider')(self.payload, self.signature)
        # TODO: assuming POST/Create
        # yield self.provider.upload_start('create')

    def data_received(self, chunk):
        """Write data to disk.

        :param str chunk: Chunk of request body
        """

        # self.provider.upload_data_received(chunk)
        # now = get_time()
        # if now > (self.last_ping + settings.PING_DEBOUNCE):
        #     self.provider.upload_ping()
        #     self.last_ping = now

    def put(self):
        """After file is uploaded, push to backend via Celery.
        """
        if not verify_file_size(self.file_pointer, self.content_length):
            self.errors.append(MESSAGES['INVALID_LENGTH'])
            raise web.HTTPError(
                httplib.BAD_REQUEST,
                reason=MESSAGES['INVALID_LENGTH'],
            )
        self.file_pointer.close()
        tasks.push_file(self.payload, self.signature, self.file_path)
        tasks.send_hook(
            {
                'status': 'success',
                'uploadSignature': self.signature,
            },
            self.payload['cachedUrl'],
        )
        self.write({'status': 'success'})

    @utils.allow_methods(['put'])
    def on_connection_close(self, *args, **kwargs):
        """Log error if connection terminated.
        """
        self.provider.upload_on_connection_close()

    @utils.allow_methods(['put'])
    def on_finish(self):
        self.provider.upload_on_finish()
