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

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.models import OSFUser, Node, Registration
from osf.models.preprint_service import PreprintService
from scripts import utils as script_utils
from website import settings
from website.app import init_app

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Sitemap(object):
    def __init__(self):
        self.sitemap_count = 0
        self.errors = 0
        self.new_doc()
        self.sitemap_dir = os.path.join(settings.STATIC_FOLDER, 'sitemaps')
        if not os.path.exists(self.sitemap_dir):
            print('Creating sitemap directory at `{}`'.format(self.sitemap_dir))
            os.makedirs(self.sitemap_dir)

    def new_doc(self):
        """Creates new sitemap document and resets the url_count."""
        self.doc = xml.dom.minidom.Document()
        self.urlset = self.doc.createElement('urlset')
        self.urlset.setAttribute('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
        self.doc.appendChild(self.urlset)
        self.url_count = 0

    def add_tag(self, name, text):
        """Adds a tag to the current url"""
        tag = self.doc.createElement(name)
        self.url.appendChild(tag)
        tag_text = self.doc.createTextNode(text)
        tag.appendChild(tag_text)

    def add_url(self, config):
        """Adds a url to the current urlset"""
        if self.url_count >= settings.SITEMAP_URL_MAX:
            self.write_doc()
            self.new_doc()
        self.url = self.doc.createElement('url')
        self.urlset.appendChild(self.url)

        for k, v in config.iteritems():
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
        sitemap_index.setAttribute('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
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

    def log_errors(self, obj, obj_id, error):
        if not self.errors:
            script_utils.add_file_logger(logger, __file__)
        self.errors += 1
        logger.info('Error on {}, {}:'.format(obj, obj_id))
        logger.exception(error)
        if self.errors == 1000:
            sentry.log_message('ERROR: generate_sitemap stopped execution after reaching 1000 errors. See logs for details.')
            raise Exception('Too many errors generating sitemap.')

    def generate(self):
        print('Generating Sitemap')
        # Static urls
        for config in settings.SITEMAP_STATIC_URLS:
            config['loc'] = urlparse.urljoin(settings.DOMAIN, config['loc'])
            self.add_url(config)

        # User urls
        for obj in OSFUser.objects.filter(is_active=True).iterator():
            try:
                config = settings.SITEMAP_USER_CONFIG
                config['loc'] = urlparse.urljoin(settings.DOMAIN, obj.url)
                self.add_url(config)
            except Exception as e:
                self.log_errors(obj, obj._id, e)

        # Node urls
        for obj in Node.objects.filter(is_public=True, is_deleted=False).iterator():
            try:
                config = settings.SITEMAP_NODE_CONFIG
                config['loc'] = urlparse.urljoin(settings.DOMAIN, obj.url)
                config['lastmod'] = obj.date_modified.isoformat()
                self.add_url(config)
            except Exception as e:
                self.log_errors(obj, obj._id, e)

        # Registration urls
        for obj in Registration.objects.filter(retraction=False, is_deleted=False, is_public=True).iterator():
            try:
                config = settings.SITEMAP_REGISTRATION_CONFIG
                config['loc'] = urlparse.urljoin(settings.DOMAIN, obj.url)
                config['lastmod'] = obj.date_modified.isoformat()
                self.add_url(config)
            except Exception as e:
                self.log_errors(obj, obj._id, e)

        # Preprint urls
        for obj in PreprintService.objects.filter(node__isnull=False, node__is_deleted=False, node__is_public=True, is_published=True).iterator():
            try:
                preprint_date = obj.date_modified.isoformat()
                config = settings.SITEMAP_PREPRINT_CONFIG
                config['loc'] = urlparse.urljoin(settings.DOMAIN, obj.url)
                config['lastmod'] = preprint_date
                self.add_url(config)

                # Preprint file urls
                try:
                    file_config = settings.SITEMAP_PREPRINT_FILE_CONFIG
                    file_config['loc'] = urlparse.urljoin(settings.DOMAIN, 
                        os.path.join('project', 
                            obj.primary_file.node._id, # Parent node id
                            'files',
                            'osfstorage',
                            obj.primary_file._id, # Preprint file deep_url
                            '?action=download'
                        )
                    )
                    file_config['lastmod'] = preprint_date
                    self.add_url(file_config)
                except Exception as e:
                    self.log_errors(obj.primary_file, obj.primary_file._id, e)
            except Exception as e:
                self.log_errors(obj, obj._id, e)

        # Final write
        self.write_doc()
        # Create index file
        self.write_sitemap_index()

        # TODO: once the sitemap is validated add a ping to google with sitemap index file location
        # TODO: server side cursor query wrapper might be useful as the index gets larger.
        # Sitemap indexable limit check
        if self.sitemap_count > settings.SITEMAP_INDEX_MAX * .90: # 10% of urls remaining
            sentry.log_message('WARNING: Max sitemaps nearly reached.')
        print('Total url_count = {}'.format((self.sitemap_count - 1) * settings.SITEMAP_URL_MAX + self.url_count))
        print('Total sitemap_count = {}'.format(str(self.sitemap_count)))
        if self.errors:
            sentry.log_message('WARNING: Generate sitemap encountered errors. See logs for details.')
            print('Total errors = {}'.format(str(self.errors)))
        else:
            print('No errors')

@celery_app.task(name='scripts.generate_sitemap')
def main():
    init_app(routes=False)  # Sets the storage backends on all models
    Sitemap().generate()

if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    main()
