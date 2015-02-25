DOCS_FORMATS = [
    {
        'ext': '.gdoc',
        'download_ext': '.docx',
        'type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    },
    {
        'ext': '.gsheet',
        'download_ext': '.xlsx',
        'type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    },
    {
        'ext': '.gslides',
        'download_ext': '.pptx',
        'type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    },
]
DOCS_DEFAULT_FORMAT = {
    'ext': '',
    'download_ext': '.pdf',
    'type': 'application/pdf',
}


def is_docs_file(metadata):
    """Only Docs files have the "exportLinks" key."""
    return metadata.get('exportLinks')


def get_format(links):
    for format in DOCS_FORMATS:
        if format['type'] in links:
            return format
    return DOCS_DEFAULT_FORMAT


def get_extension(links):
    format = get_format(links)
    return format['ext']


def get_download_extension(links):
    format = get_format(links)
    return format['download_ext']


def get_export_link(links):
    format = get_format(links)
    return links[format['type']]
