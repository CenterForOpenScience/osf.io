import http

from waterbutler.core import exceptions


def file_or_error(article, file_id):
    try:
        return next(
            each for each in article['files']
            if each['id'] == int(file_id)
        )
    except StopIteration:
        raise exceptions.MetadataError(
            'Could not resolve file with ID {0}'.format(file_id),
            code=http.client.NOT_FOUND,
        )
