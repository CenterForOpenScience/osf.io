# A list of file extension to override the content-type header for
# Fixes the issue with safari renaming files when they just return
# text/plain as their content type
mime_types = {
    '.csv': 'text/csv',
    '.md': 'text/x-markdown',
}
