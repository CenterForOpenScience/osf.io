#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate a sitemap for osf.io"""
import datetime
import gzip
import math
import os
import shutil
import sys
import urllib
import urlparse
import xml

import django
django.setup()
from django.db import transaction
import logging

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
        self.sitemap_dir = os.path.join(settings.STATIC_FOLDER, 'sitemaps')
        if not os.path.exists(self.sitemap_dir):
            print('Creating sitemap directory at `{}`'.format(self.sitemap_dir))
            os.makedirs(self.sitemap_dir)

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
        path = os.path.join(self.sitemap_dir, 'sitemap_{}.xml'.format(str(self.sitemap_count)))
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
            loc_text = self.doc.createTextNode(urlparse.urljoin(settings.DOMAIN, 'sitemaps/sitemap_{}.xml.gz'.format(str(f))))
            loc.appendChild(loc_text)

            datemod = doc.createElement('datemod')
            sitemap.appendChild(datemod)
            datemod_text = self.doc.createTextNode(datetime.datetime.now().isoformat())
            datemod.appendChild(datemod_text)

        print('Writing `sitemap_index.xml`')
        xml_str = doc.toprettyxml(indent="  ", encoding='utf-8')
        with open(os.path.join(self.sitemap_dir, 'sitemap_index.xml'), 'w') as f:
            f.write(xml_str)

    def generate(self):

        # Static urls
        static_urls = [
            ['', 'yearly'],
            ['preprints', 'yearly'],
            ['prereg', 'yearly'],
            ['meetings', 'yearly'],
            ['registries', 'yearly'],
            ['explore/activity', 'weekly'],
            ['support', 'yearly'],
            ['faq', 'yearly'],
        ]

        for url, freq in static_urls:
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, url),
                'changefreq': freq,
            })

        # User urls
        for obj in OSFUser.objects.filter(is_active=True):
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, obj.url),
                'changefreq': 'yearly',
            })

        # Node urls
        for obj in Node.objects.filter(is_public=True, is_deleted=False):
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, obj.url),
                'lastmod': obj.date_modified.isoformat(),
                'changefreq': 'monthly',
            })

        # Registration urls
        for obj in Registration.objects.filter(retraction=False, is_deleted=False, is_public=True):
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, obj.url),
                'lastmod': obj.date_modified.isoformat(),
                'changefreq': 'never',
            })

        # Preprint urls
        for obj in PreprintService.objects.filter(node__isnull=False, node__is_deleted=False, node__is_public=True, is_published=True):
            preprint_date = obj.date_modified.isoformat()
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, obj.url),
                'lastmod': preprint_date,
                'changefreq': 'monthly',
            })

            # Preprint file urls
            self.add_url(**{
                'loc': urlparse.urljoin(settings.DOMAIN, 
                    os.path.join(
                        'project', 
                        obj.primary_file.node._id, # Parent node id
                        'files',
                        'osfstorage',
                        obj.primary_file._id, # Preprint file deep_url
                        '?action=download'
                    )
                ),
                'lastmod': preprint_date,
                'changefreq': 'yearly',
            })

        # Final write
        self.write_doc()
        # Create index file
        self.write_sitemap_index()

        # TODO: once the sitemap is validated add a ping to google with sitemap index file location

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
