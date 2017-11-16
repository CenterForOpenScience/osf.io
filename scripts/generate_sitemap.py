#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate a sitemap for osf.io"""
import boto3
import datetime
import gzip
import os
import shutil
import urlparse
import xml

import django
django.setup()
import logging

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.models import OSFUser, AbstractNode, PreprintService, PreprintProvider
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
        if settings.SITEMAP_TO_S3:
            assert settings.SITEMAP_AWS_BUCKET, 'SITEMAP_AWS_BUCKET must be set for sitemap files to be sent to S3'
            assert settings.AWS_ACCESS_KEY_ID, 'AWS_ACCESS_KEY_ID must be set for sitemap files to be sent to S3'
            assert settings.AWS_SECRET_ACCESS_KEY, 'AWS_SECRET_ACCESS_KEY must be set for sitemap files to be sent to S3'
            self.s3 = boto3.resource(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name='us-east-1'
            )

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
        file_name = 'sitemap_{}.xml'.format(str(self.sitemap_count))
        file_path = os.path.join(self.sitemap_dir, file_name)
        zip_file_name = file_name + '.gz'
        zip_file_path = file_path + '.gz'
        print('Writing and gzipping `{}`: url_count = {}'.format(file_path, str(self.url_count)))

        xml_str = self.doc.toprettyxml(indent="  ", encoding='utf-8')
        with open(file_path, 'wb') as f:
            f.write(xml_str)

        # Write zipped file
        with open(file_path, 'rb') as f_in, gzip.open(zip_file_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        if settings.SITEMAP_TO_S3:
            self.ship_to_s3(file_name, file_path)
            self.ship_to_s3(zip_file_name, zip_file_path)
        self.sitemap_count += 1

    def ship_to_s3(self, name, path):
        data = open(path, 'rb')
        try:
            self.s3.Bucket(settings.SITEMAP_AWS_BUCKET).put_object(Key='sitemaps/{}'.format(name), Body=data)
        except Exception as e:
            logger.info('Error sending data to s3 via boto3')
            logger.exception(e)
            sentry.log_message('ERROR: Sitemaps could not be uploaded to s3, see `generate_sitemap` logs')
        data.close()

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
            loc_text = self.doc.createTextNode(urlparse.urljoin(settings.DOMAIN, 'sitemaps/sitemap_{}.xml'.format(str(f))))
            loc.appendChild(loc_text)

            datemod = doc.createElement('lastmod')
            sitemap.appendChild(datemod)
            datemod_text = self.doc.createTextNode(datetime.datetime.now().strftime('%Y-%m-%d'))
            datemod.appendChild(datemod_text)

        print('Writing `sitemap_index.xml`')
        file_name = 'sitemap_index.xml'
        file_path = os.path.join(self.sitemap_dir, file_name)
        xml_str = doc.toprettyxml(indent="  ", encoding='utf-8')
        with open(file_path, 'wb') as f:
            f.write(xml_str)
        if settings.SITEMAP_TO_S3:
            self.ship_to_s3(file_name, file_path)

    def log_errors(self, obj, obj_id, error):
        if not self.errors:
            script_utils.add_file_logger(logger, __file__)
        self.errors += 1
        logger.info('Error on {}, {}:'.format(obj, obj_id))
        logger.exception(error)

        if self.errors <= 10:
            sentry.log_message('Sitemap Error: {}'.format(error))

        if self.errors == 1000:
            sentry.log_message('ERROR: generate_sitemap stopped execution after reaching 1000 errors. See logs for details.')
            raise Exception('Too many errors generating sitemap.')

    def generate(self):
        print('Generating Sitemap')

        # Progress bar
        progress = script_utils.Progress()

        # Static urls
        progress.start(len(settings.SITEMAP_STATIC_URLS), 'STAT: ')
        for config in settings.SITEMAP_STATIC_URLS:
            config['loc'] = urlparse.urljoin(settings.DOMAIN, config['loc'])
            self.add_url(config)
            progress.increment()
        progress.stop()

        # User urls
        objs = OSFUser.objects.filter(is_active=True).values_list('guids___id', flat=True)
        progress.start(objs.count(), 'USER: ')
        for obj in objs:
            try:
                config = settings.SITEMAP_USER_CONFIG
                config['loc'] = urlparse.urljoin(settings.DOMAIN, '/{}/'.format(obj))
                self.add_url(config)
            except Exception as e:
                self.log_errors('USER', obj, e)
            progress.increment()
        progress.stop()

        # AbstractNode urls (Nodes and Registrations, no Collections)
        objs = (AbstractNode.objects
            .filter(is_public=True, is_deleted=False, retraction_id__isnull=True)
            .exclude(type__in=["osf.collection", "osf.quickfilesnode"])
            .values('guids___id', 'date_modified'))
        progress.start(objs.count(), 'NODE: ')
        for obj in objs:
            try:
                config = settings.SITEMAP_NODE_CONFIG
                config['loc'] = urlparse.urljoin(settings.DOMAIN, '/{}/'.format(obj['guids___id']))
                config['lastmod'] = obj['date_modified'].strftime('%Y-%m-%d')
                self.add_url(config)
            except Exception as e:
                self.log_errors('NODE', obj['guids___id'], e)
            progress.increment()
        progress.stop()

        # Preprint urls
        objs = (PreprintService.objects
                    .filter(node__isnull=False, node__is_deleted=False, node__is_public=True, is_published=True)
                    .select_related('node', 'provider', 'node__preprint_file'))
        progress.start(objs.count() * 2, 'PREP: ')
        osf = PreprintProvider.objects.get(_id='osf')
        for obj in objs:
            try:
                preprint_date = obj.date_modified.strftime('%Y-%m-%d')
                config = settings.SITEMAP_PREPRINT_CONFIG
                preprint_url = obj.url
                provider = obj.provider
                domain = provider.domain if (provider.domain_redirect_enabled and provider.domain) else settings.DOMAIN
                if provider == osf:
                    preprint_url = '/preprints/{}/'.format(obj._id)
                config['loc'] = urlparse.urljoin(domain, preprint_url)
                config['lastmod'] = preprint_date
                self.add_url(config)

                # Preprint file urls
                try:
                    file_config = settings.SITEMAP_PREPRINT_FILE_CONFIG
                    file_config['loc'] = urlparse.urljoin(
                        settings.DOMAIN,
                        os.path.join(
                            'project',
                            obj.node._id,   # Parent node id
                            'files',
                            'osfstorage',
                            obj.primary_file._id,  # Preprint file deep_url
                            '?action=download'
                        )
                    )
                    file_config['lastmod'] = preprint_date
                    self.add_url(file_config)
                except Exception as e:
                    self.log_errors(obj.primary_file, obj.primary_file._id, e)
            except Exception as e:
                self.log_errors(obj, obj._id, e)
            progress.increment(2)
        progress.stop()

        # Final write
        self.write_doc()
        # Create index file
        self.write_sitemap_index()

        # TODO: once the sitemap is validated add a ping to google with sitemap index file location
        # TODO: server side cursor query wrapper might be useful as the index gets larger.
        # Sitemap indexable limit check
        if self.sitemap_count > settings.SITEMAP_INDEX_MAX * .90:  # 10% of urls remaining
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
