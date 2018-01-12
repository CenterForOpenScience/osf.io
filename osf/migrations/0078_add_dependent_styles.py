import logging
import os

from django.db import migrations
from lxml import etree

from osf.models.citation import CitationStyle
from website import settings
from urlparse import urlparse

logger = logging.getLogger(__file__)

def get_style_files(path):
    files = (os.path.join(path, x) for x in os.listdir(path))
    return (f for f in files if os.path.isfile(f))

def update_styles(*args):
    # drop all styles
    CitationStyle.remove()

    for style_file in get_style_files(settings.CITATION_STYLES_PATH):
        with open(style_file, 'r') as f:
            try:
                root = etree.parse(f).getroot()
            except etree.XMLSyntaxError:
                continue

            namespace = root.nsmap.get(None)
            selector = '{{{ns}}}info/{{{ns}}}'.format(ns=namespace)

            title = root.find(selector + 'title').text
            # `has_bibliography` is set to `True` for Bluebook citation formats due to the special way we handle them.
            has_bibliography = root.find('{{{ns}}}{tag}'.format(ns=namespace, tag='bibliography')) is not None or 'Bluebook' in title
            # Required
            fields = {
                '_id': os.path.splitext(os.path.basename(style_file))[0],
                'title': title,
                'has_bibliography': has_bibliography,
                'parent_style': None
            }

            # Optional
            try:
                fields['short_title'] = root.find(selector + "title-short").text
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
                    parent_style = urlparse(link.get('href')).path.split('/')[-1]
                    parent_path = os.path.join(settings.CITATION_STYLES_PATH, '{}.csl'.format(parent_style))
                    with open(parent_path, 'r') as parent:
                        try:
                            parent_root = etree.parse(parent).getroot()
                        except etree.XMLSyntaxError:
                            continue
                        else:
                            parent_namespace = parent_root.nsmap.get(None)
                            parent_selector = '{{{ns}}}info/{{{ns}}}'.format(ns=parent_namespace)
                            parent_title = root.find(parent_selector + 'title').text
                            parent_has_bibliography = parent_root.find('{{{ns}}}{tag}'.format(ns=parent_namespace, tag='bibliography')) is not None or 'Bluebook' in parent_title
                            fields = {
                                '_id': style_id,
                                'title': title,
                                'has_bibliography': parent_has_bibliography,
                                'parent_style': os.path.splitext(os.path.basename(parent_style))[0]
                            }

                            # Optional
                            try:
                                fields['short_title'] = root.find(selector + "title-short").text
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
                fields = {
                    '_id': style_id,
                    'title': title,
                    'has_bibliography': has_bibliography,
                    'parent_style': None
                }
                style = CitationStyle(**fields)
                style.save()


def revert(*args):
    # The revert of this migration simply removes all CitationStyle instances.
    CitationStyle.remove()

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0077_citationstyle_parent_style'),
    ]

    operations = [
        migrations.RunPython(update_styles, revert),
    ]
