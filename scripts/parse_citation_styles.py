#!/usr/bin/env python
# encoding: utf-8

"""
This script is modified in this PR (https://github.com/CenterForOpenScience/osf.io/pull/7595)
to set the corresponding `has_bibliography` flag to `False` for all citation formats whose CSL file do not
include a bibliography section. As a result, all such citation formats would not show up in OSF
citation widgets for users to choose.

NOTE:
As of August 25th, 2017, there are however THREE EXCEPTIONS:
"Bluebook Law Review", "Bluebook Law Review(2)" and "Bluebook Inline" shares a
special CSL file ('website/static/bluebook.cls'), in which a bibliography section is defined,
for rendering bibliographies even though their official CSL files (located in assets folder)
do not contain a bibliography section.
The side effect is that, upon parsing all the CSL files in the assets folder, these three citation
formats are marked as `has_bibliography=False`, preventing them from user selection on the front end.
Therefore, intervention is needed to manually "turn on" their 'has_bibliography' flag for them to show
on the citation widget.
"""

import os

from lxml import etree

from website import settings
from website.app import setup_django
setup_django()
from osf.models.citation import CitationStyle

def main():

    # drop all styles
    CitationStyle.objects.all().delete()

    total = 0

    for style_file in get_style_files(settings.CITATION_STYLES_PATH):
        with open(style_file, 'r') as f:
            try:
                root = etree.parse(f).getroot()
            except etree.XMLSyntaxError:
                continue
            total += 1
            namespace = root.nsmap.get(None)
            selector = '{{{ns}}}info/{{{ns}}}'.format(ns=namespace)

            # Required
            fields = {
                '_id': os.path.splitext(os.path.basename(style_file))[0],
                'title': root.find(selector + 'title').text,
                'has_bibliography': True if root.find(
                    '{{{ns}}}{tag}'.format(ns=namespace, tag='bibliography')) is not None else False
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

    return total


def get_style_files(path):
    files = (os.path.join(path, x) for x in os.listdir(path))
    return (f for f in files if os.path.isfile(f))


if __name__ == '__main__':
    total = main()
    print("Parsed {} styles".format(total))
