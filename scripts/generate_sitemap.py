#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Populate development database with PreprintProvider fixtures"""
import gzip
import logging
import math
import shutil
import sys
import urllib

import django
from django.db import transaction
from modularodm import Q
django.setup()

from website import settings
from website.app import init_app
import datetime
from framework.sentry import log_exception
from django.db import transaction
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from website.app import init_app
from osf.models import OSFUser, Node, Registration
from osf.models.preprint_service import PreprintService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BASE_URL = 'localhost:5000'

from xml.dom import minidom


class Sitemap(object):
    def __init__(self):
        self.file_count = 0
        # ajs: This max_records was chosen to be sufficiently lower than the 5mb per file limit given in spec. 
        # It was not clear whether 5mb was pre or post gzip. This could be revisited if limits are reached.
        self.max_records = 24999
        self.new_doc()
        self.BASE_URL = 'http://localhost:5000'

    def new_doc(self):
        self.doc = minidom.Document()
        self.urlset = self.doc.createElement('urlset')
        self.doc.appendChild(self.urlset)
        self.record_count = 0

    def add_line(self, name, text):
        line = self.doc.createElement(name)
        self.url.appendChild(line)
        line_text = self.doc.createTextNode(text)
        line.appendChild(line_text)

    def add_record(self, **kwargs):
        if self.record_count > self.max_records:
            self.write_doc()
            self.new_doc()
        self.url = self.doc.createElement('url')
        self.urlset.appendChild(self.url)

        for key, val in kwargs.iteritems():
            self.add_line(key, val)

        self.record_count += 1

    def write_doc(self):
        print 'Writing `sitemap_' + str(self.file_count) + '.xml`: ' + str(self.record_count) + ' records'
        xml_str = self.doc.toprettyxml(indent="  ", encoding='utf-8')
        with open(settings.STATIC_FOLDER + '/sitemaps/sitemap_' + str(self.file_count) + '.xml', 'w') as f:
            f.write(xml_str)
        self.file_count += 1

    def generate_users(self):
        for obj in OSFUser.objects.all():
            self.add_record(**{
                'loc': self.BASE_URL + obj.url,
                'changefreq': 'yearly',
            })

    def generate_test(self):
        import random
        guider = 'abcdefghijklmnopqrstuvwxyz1234567890'
        for _ in range(100000):
            my_guid = ''
            for i in range(5):
                my_guid += guider[random.randint(0,35)]
            self.add_record(**{
                'loc': self.BASE_URL + '/' + my_guid + '/',
                'lastmod': datetime.datetime.now().isoformat(),
                'changefreq': 'monthly',
            })

    def generate_nodes(self):
        for obj in Node.objects.filter(is_public=True):
            self.add_record(**{
                'loc': self.BASE_URL + obj.url,
                'lastmod': obj.date_modified.isoformat(),
                'changefreq': 'monthly',
            })

    def generate_registrations(self):
        for obj in Registration.objects.filter(retraction=False):
            self.add_record(**{
                'loc': self.BASE_URL + obj.url,
                'lastmod': obj.date_modified.isoformat(),
                'changefreq': 'monthly',
            })

    def generate_preprints(self):
        for obj in PreprintService.objects.filter(node__isnull=False):
            self.add_record(**{
                'loc': self.BASE_URL + obj.url,
                'lastmod': obj.date_modified.isoformat(),
                'changefreq': 'monthly',
            })

    def generate_static(self):
        static = [
            '/',
            '/preprints/',
            '/prereg/',
            '/meetings/',
            '/registries/',
            '/explore/activity/',
            '/support/',
        ]

        for s in static:
            self.add_record(**{
                'loc': self.BASE_URL + s,
                'change_freq': 'yearly',
            })

    def gzip_sitemaps(self):
        for f in range(self.file_count):
            path = settings.STATIC_FOLDER + '/sitemaps/sitemap_' + str(f) + '.xml'
            with open(path, 'rb') as f_in, gzip.open(path + '.gz', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def write_sitemap_index(self):
        doc = minidom.Document()
        sitemap_index = self.doc.createElement('sitemapindex')
        doc.appendChild(sitemap_index)
        for f in range(self.file_count):
            sitemap = doc.createElement('sitemap')
            sitemap_index.appendChild(sitemap)
            
            loc = doc.createElement('loc')
            sitemap.appendChild(loc)
            loc_text = self.doc.createTextNode(self.BASE_URL + '/sitemaps/sitemap_' + str(f) + '.xml.gz ')
            loc.appendChild(loc_text)

            datemod = doc.createElement('datemod')
            sitemap.appendChild(datemod)
            datemod_text = self.doc.createTextNode(datetime.datetime.now().isoformat())
            datemod.appendChild(datemod_text)

        print 'Writing `sitemap_index.xml`'
        xml_str = doc.toprettyxml(indent="  ", encoding='utf-8')
        with open(settings.STATIC_FOLDER + '/sitemaps/sitemap_index.xml', 'w') as f:
            f.write(xml_str)

    def generate(self):
        self.generate_static()
        self.generate_nodes()
        self.generate_users()
        self.generate_nodes()
        self.generate_preprints()
        self.generate_registrations()

        self.generate_test()
        
        self.write_doc()
        self.gzip_sitemaps()
        self.write_sitemap_index()

        if self.file_count > 49500:
            # Life goals
            logger.exception('WARNING: Max sitemaps nearly reached: ' + str(self.file_count + 1) + ' of 50000 max sitemaps for index file')
            log_exception()

def main():
    init_app(routes=False)  # Sets the storage backends on all models
    Sitemap().generate()

if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    main()
