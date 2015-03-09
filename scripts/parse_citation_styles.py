#!/usr/bin/env python
# encoding: utf-8

import os

from lxml import etree

from website import settings
from website.app import init_app
from website.models import CitationStyle


def main():
    init_app(set_backends=True, routes=False)

    # drop all styles
    CitationStyle.remove()

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
