import logging
import os

from django.db import migrations
from lxml import etree

from website import settings
from future.moves.urllib.parse import urlparse

logger = logging.getLogger(__file__)

def get_style_files(path):
    files = (os.path.join(path, x) for x in os.listdir(path))
    return (f for f in files if os.path.isfile(f))

def update_styles(state, schema):
    # drop all styles
    CitationStyle = state.get_model('osf', 'citationstyle')
    CitationStyle.objects.all().delete()

    for style_file in get_style_files(settings.CITATION_STYLES_PATH):
        with open(style_file, 'r') as f:
            try:
                root = etree.parse(f).getroot()
            except etree.XMLSyntaxError:
                continue

            namespace = root.nsmap.get(None)
            selector = '{{{ns}}}info/{{{ns}}}'.format(ns=namespace)
            title = root.find(selector + 'title').text
            has_bibliography = 'Bluebook' in title

            if not has_bibliography:
                bib = root.find('{{{ns}}}{bib}'.format(ns=namespace, bib='bibliography'))
                layout = bib.find('{{{ns}}}{layout}'.format(ns=namespace, layout='layout')) if bib is not None else None
                has_bibliography = True
                if layout is not None and len(layout.getchildren()) == 1 and 'choose' in layout.getchildren()[0].tag:
                    choose = layout.find('{{{ns}}}{choose}'.format(ns=namespace, choose='choose'))
                    else_tag = choose.find('{{{ns}}}{tag}'.format(ns=namespace, tag='else'))
                    if else_tag is None:
                        supported_types = []
                        match_none = False
                        for child in choose.getchildren():
                            types = child.get('type', None)
                            match_none = child.get('match', 'any') == 'none'
                            if types is not None:
                                types = types.split(' ')
                                supported_types.extend(types)

                                if 'webpage' in types:
                                    break
                        else:
                            if len(supported_types) and not match_none:
                                # has_bibliography set to False now means that either bibliography tag is absent
                                # or our type (webpage) is not supported by the current version of this style.
                                has_bibliography = False

            # Required
            fields = {
                '_id': os.path.splitext(os.path.basename(style_file))[0],
                'title': title,
                'has_bibliography': has_bibliography,
                'parent_style': None
            }

            # Optional
            try:
                fields['short_title'] = root.find(selector + 'title-short').text
            except AttributeError:
                pass

            try:
                fields['summary'] = root.find(selector + 'summary').text
            except AttributeError:
                pass

            style = CitationStyle(**fields)
            style.save()

    # Parse styles under styles/dependent that depend on some styles under styles.

    dependent_dir = os.path.join(settings.CITATION_STYLES_PATH, 'dependent')
    for style_file in get_style_files(dependent_dir):
        with open(style_file, 'r') as f:
            try:
                root = etree.parse(f).getroot()
            except etree.XMLSyntaxError:
                continue

            namespace = root.nsmap.get(None)
            selector = '{{{ns}}}info/{{{ns}}}'.format(ns=namespace)
            title = root.find(selector + 'title').text
            has_bibliography = root.find('{{{ns}}}{tag}'.format(ns=namespace, tag='bibliography')) is not None or 'Bluebook' in title

            style_id = os.path.splitext(os.path.basename(style_file))[0]
            links = root.findall(selector + 'link')
            for link in links:
                if link.get('rel') == 'independent-parent':
                    parent_style_id = urlparse(link.get('href')).path.split('/')[-1]
                    parent_style = CitationStyle.objects.get(_id=parent_style_id)

                    if parent_style is not None:
                        parent_has_bibliography = parent_style.has_bibliography
                        fields = {
                            '_id': style_id,
                            'title': title,
                            'has_bibliography': parent_has_bibliography,
                            'parent_style': parent_style_id
                        }

                        # Optional
                        try:
                            fields['short_title'] = root.find(selector + 'title-short').text
                        except AttributeError:
                            pass

                        try:
                            fields['summary'] = root.find(selector + 'summary').text
                        except AttributeError:
                            pass

                        style = CitationStyle(**fields)
                        style.save()
                        break

                    else:
                        logger.debug('Unable to load parent_style object: parent {}, dependent style {}'.format(parent_style_id, style_id))
            else:
                fields = {
                    '_id': style_id,
                    'title': title,
                    'has_bibliography': has_bibliography,
                    'parent_style': None
                }
                style = CitationStyle(**fields)
                style.save()


def revert(state, schema):
    # The revert of this migration simply removes all CitationStyle instances.
    CitationStyle = state.get_model('osf', 'citationstyle')
    CitationStyle.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0106_citationstyle_parent_style'),
    ]

    operations = [
        migrations.RunPython(update_styles, revert),
    ]
