import os
import difflib
import requests
import progressbar
from pyquery import PyQuery
from distutils.dir_util import mkpath

yorm_osf = 'http://localhost:5000'
modm_osf = 'http://localhost:5001'

def crawl(name, urls):

    path, _ = os.path.split(__file__)
    save_path = os.path.join(path, 'diffs', name)
    mkpath(save_path)

    with \
            open('%s/diffs.txt' % (save_path), 'w') as diffs, \
            open('%s/httperrors.txt' % (save_path), 'w') as httperrors, \
            open('%s/flaskerrors.txt' % (save_path), 'w') as flaskerrors:

        progress = progressbar.ProgressBar(maxval=len(urls)).start()

        for idx, path in enumerate(urls):

            a = requests.get(yorm_osf + path.strip()).content
            try:
                a_title = PyQuery(a)('title').text() or ''
            except:
                pass
            a = a.replace('\t', '    ')
            a_lines = [line for line in a.split('\n') if line]

            b = requests.get(modm_osf + path.strip()).content
            try:
                b_title = PyQuery(b)('title').text() or ''
            except:
                pass
            b = b.replace('\t', '    ')
            b_lines = [line for line in b.split('\n') if line]
            
            if a_lines != b_lines:
                diff = difflib.context_diff(a_lines, b_lines)
                diffs.write(path)
                diffs.write('\n')
                diffs.writelines(diff)
                diffs.write('\n\n')

            if '404 Not Found' in [a_title, b_title]:
                httperrors.write(path)
                diffs.write('\n')
                httperrors.write('Error: 404')
                httperrors.write('\n\n')

            if 'Werkzeug Debugger' in a_title or 'Werkzeug Debugger' in b_title:
                flaskerrors.write(path)
                diffs.write('\n')
                flaskerrors.write('Werkzeug Error')
                flaskerrors.write('\n\n')

            progress.update(idx)

        progress.finish()
