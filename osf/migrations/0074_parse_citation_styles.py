# This migration port `scripts/parse_citation_styles` to automatically parse citation styles.
# Additionally, this set the corresponding `has_bibliography` field to `False` for all citation formats whose CSL files do not
# include a bibliography section. As a result, all such citation formats would not show up in OSF
# citation widgets for users to choose.
#
# NOTE:
# As of December 6th, 2017, there are however THREE EXCEPTIONS:
# "Bluebook Law Review", "Bluebook Law Review(2)" and "Bluebook Inline" shares a
# special CSL file ('website/static/bluebook.cls'), in which a bibliography section is defined,
# in order to render bibliographies even though their official CSL files (located in CenterForOpenScience/styles repo)
# do not contain a bibliography section. Therefore, This migration also automatically set `has_bibliography` to `True` for all styles whose titles contain "Bluebook"

import logging
import os

from django.db import migrations
from lxml import etree

from website import settings

logger = logging.getLogger(__file__)

def get_style_files(path):
    files = (os.path.join(path, x) for x in os.listdir(path))
    return (f for f in files if os.path.isfile(f))

def parse_citation_styles(state, schema):
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
            # `has_bibliography` is set to `True` for Bluebook citation formats due to the special way we handle them.
            has_bibliography = root.find('{{{ns}}}{tag}'.format(ns=namespace, tag='bibliography')) is not None or 'Bluebook' in title
            # Required
            fields = {
                '_id': os.path.splitext(os.path.basename(style_file))[0],
                'title': title,
                'has_bibliography': has_bibliography,
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

def revert(state, schema):
    # The revert of this migration simply removes all CitationStyle instances.
    CitationStyle = state.get_model('osf', 'citationstyle')
    CitationStyle.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0073_citationstyle_has_bibliography'),
    ]

    operations = [
        migrations.RunPython(parse_citation_styles, revert),
    ]
