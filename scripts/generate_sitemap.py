#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate development database with PreprintProvider fixtures"""
import datetime
import gzip
import logging
import math
import shutil
import sys
import urllib
import urlparse
import xml
import os

import django
django.setup()
from django.db import transaction

from framework.celery_tasks import app as celery_app
from framework.sentry import log_exception
from osf.models import OSFUser, Node, Registration
from osf.models.preprint_service import PreprintService
from website import settings
from website.app import init_app

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Sitemap(object):
    def __init__(self):
        self.sitemap_count = 0
        # ajs: This url_max was chosen to be sufficiently lower than the 5mb per file limit given in spec. 
        # It was not clear whether 5mb was pre or post gzip. This could be revisited if limits are reached.
        self.url_max = 24999
        self.new_doc()

    def new_doc(self):
        """Creates new sitemap document and resets the url_count."""
        self.doc = xml.dom.minidom.Document()
        self.urlset = self.doc.createElement('urlset')
        self.doc.appendChild(self.urlset)
        self.url_count = 0

    def add_tag(self, name, text):
        """Adds a tag to the current url"""
        tag = self.doc.createElement(name)
        self.url.appendChild(tag)
        tag_text = self.doc.createTextNode(text)
        tag.appendChild(tag_text)

    def add_url(self, **kwargs):
        """Adds a url to the current urlset"""
        if self.url_count > self.url_max:
            self.write_doc()
            self.new_doc()
        self.url = self.doc.createElement('url')
        self.urlset.appendChild(self.url)

        for k, v in kwargs.iteritems():
            self.add_tag(k, v)
        self.url_count += 1

    def write_doc(self):
        """Writes and gzips each sitemap xml file"""
        path = os.path.join(settings.STATIC_FOLDER, 'sitemaps', 'sitemap_{}.xml'.format(str(self.sitemap_count)))
        print('Writing and gzipping `{}`: url_count = {}'.format(path, str(self.url_count)))

        xml_str = self.doc.toprettyxml(indent="  ", encoding='utf-8')
        with open(path, 'w') as f:
            f.write(xml_str)
        # Write zipped file
        with open(path, 'rb') as f_in, gzip.open(path + '.gz', 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        self.sitemap_count += 1

    def write_sitemap_index(self):
        """Writes the index file for all of the sitemap files"""
        doc = xml.dom.minidom.Document()
        sitemap_index = self.doc.createElement('sitemapindex')
        doc.appendChild(sitemap_index)

        for f in range(self.sitemap_count):
            sitemap = doc.createElement('sitemap')
            sitemap_index.appendChild(sitemap)
            
            loc = doc.createElement('loc')
            sitemap.appendChild(loc)
            loc_text = self.doc.createTextNode(os.path.join(settings.DOMAIN, 'sitemaps', 'sitemap_{}.xml.gz'.format(str(f))))
            loc.appendChild(loc_text)

            datemod = doc.createElement('datemod')
            sitemap.appendChild(datemod)
            datemod_text = self.doc.createTextNode(datetime.datetime.now().isoformat())
            datemod.appendChild(datemod_text)

        print('Writing `sitemap_index.xml`')
        xml_str = doc.toprettyxml(indent="  ", encoding='utf-8')
        with open('{}/sitemaps/sitemap_index.xml'.format(settings.STATIC_FOLDER), 'w') as f:
            f.write(xml_str)

    def generate(self):

        # Static urls
        static_urls = [
            '',
            'preprints',
            'prereg',
            'meetings',
            'registries',
            'explore/activity',
            'support',
        ]

        for url in static_urls:
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, url),
                'change_freq': 'yearly',
            })

        # User urls
        for obj in OSFUser.objects.all():
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, obj.url),
                'changefreq': 'yearly',
            })

        # Node urls
        for obj in Node.objects.filter(is_public=True):
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, obj.url),
                'lastmod': obj.date_modified.isoformat(),
                'changefreq': 'monthly',
            })

        # Registration urls
        for obj in Registration.objects.filter(retraction=False):
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, obj.url),
                'lastmod': obj.date_modified.isoformat(),
                'changefreq': 'never',
            })

        # Preprint urls
        for obj in PreprintService.objects.filter(node__isnull=False):
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, obj.url),
                'lastmod': obj.date_modified.isoformat(),
                'changefreq': 'monthly',
            })

            # Preprint file urls
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, os.path.join('project', obj.primary_file.node._id, 'files', 'osfstorage', obj.primary_file._id, '?action=download')),
                'lastmod': obj.date_modified.isoformat(),
                'changefreq': 'yearly',
            })

        # Final write and index
        self.write_doc()
        self.write_sitemap_index()

        # Sitemap indexable limit check (#osflifegoals)
        if self.sitemap_count > 49500:
            logger.exception('WARNING: Max sitemaps nearly reached: {} of 50000 max sitemaps for index file'.format(str(self.sitemap_count)))
            log_exception()
        print('Total url_count = {}'.format((self.sitemap_count - 1) * (self.url_max + 1) + self.url_count))
        print('Total sitemap_count = {}'.format(str(self.sitemap_count)))

@celery_app.task(name='scripts.generate_sitemap')
def main():
    init_app(routes=False)  # Sets the storage backends on all models
    Sitemap().generate()

if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    main()
