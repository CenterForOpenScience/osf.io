# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os.path
from io import BytesIO
import datetime
import pytz
import re
import json
import requests
import urllib
import csv
import pandas as pd
import numpy as np
import hashlib

from django.apps import apps
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.core import mail
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
# from OSF
from osf.models import (
    Institution,
    OSFUser,
    AbstractNode,
    RdmStatistics)
from website import settings as website_settings
from website.settings import SUPPORT_EMAIL
from website.util import waterbutler_api_url_for
import matplotlib as mpl           # noqa
mpl.use('Agg')                     # noqa
import matplotlib.pyplot as plt    # noqa
import matplotlib.ticker as ticker  # noqa
from matplotlib.backends.backend_agg import FigureCanvasAgg
import seaborn as sns
#from reportlab.pdfgen import canvas
import pdfkit
# from admin and rdm
from admin.base import settings
from admin.rdm.utils import RdmPermissionMixin, get_dummy_institution
from admin.rdm_addons import utils


RANGE_STATISTICS = 10
STATISTICS_IMAGE_WIDTH = 8
STATISTICS_IMAGE_HEIGHT = 4
RECURSIVE_LIMIT = 10000
WB_MAX_RETRY = 3
SITE_KEY = 'rdm_statistics'

class InstitutionListViewStat(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    """institlutions list view for statistics"""
    template_name = 'rdm_statistics/institution_list.html'
    raise_exception = True

    def test_func(self):
        """validate user permissions"""
        if not self.is_authenticated:
            return False
        # allow superuser and institution_administrator
        if self.is_super_admin or self.is_admin:
            return True
        return False

    def get(self, request, *args, **kwargs):
        """get contexts"""
        user = self.request.user
        # supseruser
        if self.is_super_admin:
            ctx = {
                'institutions': Institution.objects.order_by('id').all(),
                'logohost': settings.OSF_URL,
            }
            return self.render_to_response(ctx)
        # institution_admin
        elif self.is_admin:
            institution = user.affiliated_institutions.first()
            if institution:
                return redirect(reverse('statistics:statistics', args=[institution.id]))
            else:
                # admin not affiliated institution
                raise PermissionDenied
        else:
            # not superuser, or admin
            raise PermissionDenied


class StatisticsView(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    """index view of statistics module."""
    template_name = 'rdm_statistics/statistics.html'
    raise_exception = True

    def test_func(self):
        """validate user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get_context_data(self, **kwargs):
        """get contexts"""
        ctx = super(StatisticsView, self).get_context_data(**kwargs)
        user = self.request.user
        institution_id = int(kwargs['institution_id'])
        if Institution.objects.filter(pk=institution_id).exists():
            institution = Institution.objects.get(pk=institution_id)
        else:
            institution = get_dummy_institution()
        if institution:
            ctx['institution'] = institution
        current_date = get_current_date()
        start_date = get_start_date(end_date=current_date)
        provider_data_array = get_provider_data_array(institution=institution,
                                                      start_date=start_date, end_date=current_date)
        ctx['current_date'] = current_date
        ctx['user'] = user
        ctx['provider_data_array'] = provider_data_array
        digest = hashlib.sha512(SITE_KEY).hexdigest()
        ctx['token'] = digest.upper()
        return ctx


class ProviderData(object):
    """create provider stat data"""
    raise_exception = True

    def __init__(self, provider, institution, start_date, end_date):
        self.provider = provider
        self.start_date = start_date
        self.end_date = end_date
        self.institution = institution
        self.statistics_data_array = []
        self.__create_statistics_data()
        self.statistics_data_array = self.__get_statistics_data_array()

    def get_data(self, data_type):
        """get data by type"""
        if data_type == 'num':
            return self.statistics_data_array[0]
        elif data_type == 'size':
            return self.statistics_data_array[1]
        else:
            return self.statistics_data_array[2]

    def __get_statistics_data_array(self, **kwargs):
        """get data"""
        return [self.__get_statistics_data(data_type='num'),
                self.__get_statistics_data(data_type='size'),
                self.__get_statistics_data(data_type='ext')]

    def __create_statistics_data(self, data_type='ext', **kwargs):
        """get data"""
        self.stat_data = RdmStatistics.objects.filter(institution=self.institution,
                                                      provider=self.provider, date_acquired__lte=self.end_date).\
                                                      filter(date_acquired__gte=self.start_date)
        # file extention list
        extentions = self.stat_data.values_list('extention_type', flat=True)
        self.ext_list = np.unique(extentions)
        self.ext_list.sort()
        self.date_list = self.stat_data.values_list('date_acquired', flat=True)
        self.x_tk = np.unique(map(lambda x: x.strftime('%Y/%m/%d'), self.date_list))
        self.x_tk.sort()
        self.left = np.unique(map(lambda x: x.strftime('%Y-%m-%d'), self.date_list))
        cols = ['left', 'height', 'type']
        self.size_df = pd.DataFrame(index=[], columns=cols)
        self.number_df = pd.DataFrame(index=[], columns=cols)
        for ext in self.ext_list:
            size_row_list = []
            number_row_list = []
            for acquired_date in self.left:
                entries = self.stat_data.filter(date_acquired=acquired_date, extention_type=ext)
                sum_size = 0
                sum_number = 0
                for entry in entries:
                    sum_size += entry.subtotal_file_size
                    sum_number += entry.subtotal_file_number
                size_row_list.append(sum_size)
                number_row_list.append(sum_number)
            self.size_df = self.size_df.append(pd.DataFrame({'left': self.left,
                                                             'height': size_row_list,
                                                             'type': ext}))
            self.number_df = self.number_df.append(pd.DataFrame({'left': self.left,
                                                                 'height': number_row_list,
                                                                 'type': ext}))
        self.size_df.fillna(0)
        self.number_df.fillna(0)

    def __get_statistics_data(self, data_type='ext', **kwargs):
        """get data"""
        statistics_data = StatisticsData(self.provider, self.end_date)
        statistics_data.label = self.x_tk
        statistics_data.data_type = data_type
        if data_type == 'num':
            number_df_sum = self.number_df.groupby('left', as_index=False).sum()
            statistics_data.df = self.number_df
            number_sum_list = list(number_df_sum['height'].values.flatten())
            statistics_data.title = 'Number of files'
            statistics_data.y_label = 'File Numbers'
            statistics_data.add('number', number_sum_list)
            statistics_data.graphstyle = 'whitegrid'
            statistics_data.background = '#EEEEFF'
            statistics_data.image_string = create_image_string(statistics_data.provider,
                                                               statistics_data=statistics_data)
        elif data_type == 'size':
            size_df_sum = self.size_df.groupby('left', as_index=False).sum()
            statistics_data.df = self.size_df
            size_sum_list = list(size_df_sum['height'].values.flatten())
            statistics_data.title = 'Subtotal of file sizes'
            statistics_data.y_label = 'File Sizes'
            statistics_data.add('size', map(lambda x: approximate_size(x, True), size_sum_list))
            statistics_data.graphstyle = 'whitegrid'
            statistics_data.background = '#EEFFEE'
            statistics_data.image_string = create_image_string(statistics_data.provider, statistics_data=statistics_data)
        else:
            statistics_data.df = self.number_df
            statistics_data.title = 'Number of files by extension type'
            statistics_data.y_label = 'File Numbers'
            statistics_data.graphstyle = 'whitegrid'
            statistics_data.background = '#FFEEEE'
            for ext in self.ext_list:
                statistics_data.add(ext, self.number_df[self.number_df['type'] == ext].height.values.tolist())
            statistics_data.image_string = create_image_string(statistics_data.provider, statistics_data=statistics_data)
        return statistics_data

class StatisticsData(object):
    """display graph image"""
    raise_exception = True

    def __init__(self, provider, current_date):
        self.provider = provider
        self.current_date = current_date
        # self.provider_id = 0
        self.data_type = ''
        self.graphstyle = 'darkgrid'
        self.background = '#CCCCFF'
        self.title = ''
        self.data = {}
        self.df = {}
        self.label = []
        self.x_label = 'DATE'
        self.y_label = 'File Numbers'
        self.image_str = ''

    def add(self, ext, data):
        'add data'
        self.data[ext] = data


def get_provider_data_array(institution, start_date, end_date, **kwargs):
    """retrieve statistics data array by provider"""
    provider_list_data = RdmStatistics.objects.filter(institution=institution, date_acquired__lte=end_date).\
                                            filter(date_acquired__gte=start_date).values_list('provider', flat=True)\
                                            .order_by('provider').distinct()
    provider_list = np.unique(provider_list_data)
    provider_data_array = []
    for provider in provider_list:
        provider_data = ProviderData(provider=provider, institution=institution,
                                     start_date=start_date, end_date=end_date)
        provider_data_array.append(provider_data)
    return provider_data_array

def create_image_string(provider, statistics_data):
    cols = ['left', 'height', 'type']
    data = pd.DataFrame(index=[], columns=cols)
    left = statistics_data.label
    if statistics_data.data_type == 'ext':
        data = statistics_data.df
    else:
        size_df_sum = statistics_data.df.groupby('left', as_index=False).sum()
        size_sum_list = list(size_df_sum['height'].values.flatten())
        data = pd.DataFrame({'left': left, 'height': size_sum_list,
                             'type': statistics_data.data_type})

    # fig properties
    fig = plt.figure(figsize=(STATISTICS_IMAGE_WIDTH, STATISTICS_IMAGE_HEIGHT))
    sns.set_style(statistics_data.graphstyle)
    fig.patch.set_facecolor(statistics_data.background)
    ax = sns.pointplot(x='left', y='height', hue='type', data=data)
    ax.set_xticklabels(labels=statistics_data.label, rotation=20)
    ax.set_xlabel(xlabel=statistics_data.x_label)
    ax.set_ylabel(ylabel=statistics_data.y_label)
    ax.set_title(statistics_data.title + ' in ' + provider)
    ax.tick_params(labelsize=9)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.legend(loc='upper right', bbox_to_anchor=(1.1255555, 1), ncol=1, borderaxespad=1, shadow=True)
    canvas = FigureCanvasAgg(fig)
    png_output = BytesIO()
    canvas.print_png(png_output)
    img_data = urllib.quote(png_output.getvalue())
    plt.close()
    return img_data

def create_pdf(request, is_pdf=True, **kwargs):
    """download pdf"""
    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied
    if not (user.is_superuser or user.is_staff):
        raise PermissionDenied
    institution_id = int(kwargs['institution_id'])
    if Institution.objects.filter(pk=institution_id).exists():
        institution = Institution.objects.get(pk=institution_id)
    else:
        institution = get_dummy_institution()
    current_date = get_current_date()
    start_date = get_start_date(end_date=current_date)
    provider_data_array = get_provider_data_array(institution=institution, start_date=start_date, end_date=current_date)
    template_name = 'rdm_statistics/statistics_report.html'
    # context data
    ctx = {}
    if institution:
        ctx['institution'] = institution
    ctx['current_date'] = current_date
    ctx['user'] = user
    ctx['provider_data_array'] = provider_data_array
    html_string = render_to_string(template_name, ctx)
    # if html
    if is_pdf:
        # if PDF
        try:
            converted_pdf = convert_to_pdf(html_string=html_string, file=False)
            pdf_file_name = 'statistics.' + current_date.strftime('%Y%m%d') + '.pdf'
            response = HttpResponse(converted_pdf, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="' + pdf_file_name + '"'
            return response
        except OSError as e:
            response = HttpResponse(str(e), content_type='text/html', status=501)
        except Exception as e:
            response = HttpResponse(str(e), content_type='text/html', status=501)
    else:
        response = HttpResponse(html_string, content_type='text/html')
    return response

def convert_to_pdf(html_string, file=False):
    # wkhtmltopdf settings
    wkhtmltopdf_path = os.path.join(os.path.dirname(__file__), '.', 'wkhtmltopdf')
    # print wkhtmltopdf_path
    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
    options = {
        'page-size': 'A4',
        'margin-top': '0.50in',
        'margin-right': '0.60in',
        'margin-bottom': '0.60in',
        'margin-left': '0.60in'
    }
    current_date = get_current_date()
    # if file
    if file:
        pdf_file_name = 'statistics.' + current_date.strftime('%Y%m%d') + '.pdf'
        converted_pdf = pdf_file_name
    else:
        converted_pdf = pdfkit.from_string(html_string, False,
                                           configuration=config, options=options)
    return converted_pdf

def get_start_date(end_date):
    start_date = end_date - datetime.timedelta(weeks=(RANGE_STATISTICS))\
        + datetime.timedelta(days=(1))
    return start_date

def create_csv(request, **kwargs):
    """download pdf"""
    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied
    if not (user.is_superuser or user.is_staff):
        raise PermissionDenied
    institution_id = int(kwargs['institution_id'])
    if Institution.objects.filter(pk=institution_id).exists():
        institution = Institution.objects.get(pk=institution_id)
    else:
        institution = get_dummy_institution()
    current_date = get_current_date()
    csv_data = get_all_statistic_data_csv(institution=institution)
    csv_file_name = 'statistics.all.' + current_date.strftime('%Y%m%d') + '.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=' + csv_file_name
    writer = csv.writer(response, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows(csv_data)
    return response

def get_all_statistic_data_csv(institution, **kwargs):
    target_fields = ['provider', 'extention_type', 'subtotal_file_number', 'subtotal_file_size', 'date_acquired']
    all_stat_dict = RdmStatistics.objects.filter(institution=institution).order_by('provider', 'extention_type', 'date_acquired').values(*target_fields)
    # csv data list
    header_list = ['institution_name']
    header_list.extend(target_fields)
    csv_data_list = []
    csv_data_list.append(header_list)
    for row in all_stat_dict:
        row_list = [institution.name]
        for field in target_fields:
            row_list.append(row[field])
        csv_data_list.append(row_list)
    return csv_data_list

class ImageView(RdmPermissionMixin, UserPassesTestMixin, View):
    """display graph image (return response object as img/png)"""
    raise_exception = True

    def test_func(self):
        """validate user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        if not self.is_authenticated:
            return False
        if self.is_super_admin or self.is_admin:
            return self.has_auth(institution_id)
        return False

    def get(self, request, *args, **kwargs):
        """get context data"""
        graph_type = self.kwargs.get('graph_type')
        provider = self.kwargs.get('provider')
        institution_id = int(self.kwargs.get('institution_id'))
        if Institution.objects.filter(pk=institution_id).exists():
            institution = Institution.objects.get(pk=institution_id)
        else:
            institution = get_dummy_institution()

        # create provider data
        provider_data = self.__get_data(provider=provider, institution=institution)
        cols = ['left', 'height', 'type']
        data = pd.DataFrame(index=[], columns=cols)
        statistics_data = provider_data.get_data(data_type=graph_type)
        left = statistics_data.label
        if statistics_data.data_type == 'ext':
            data = statistics_data.df
        else:
            size_df_sum = statistics_data.df.groupby('left', as_index=False).sum()
            size_sum_list = list(size_df_sum['height'].values.flatten())
            data = pd.DataFrame({'left': left, 'height': size_sum_list, 'type': statistics_data.data_type})
        fig = plt.figure(figsize=(STATISTICS_IMAGE_WIDTH, STATISTICS_IMAGE_HEIGHT))
        sns.set_style(statistics_data.graphstyle)
        fig.patch.set_facecolor(statistics_data.background)
        ax = sns.pointplot(x='left', y='height', hue='type', data=data)
        ax.set_xticklabels(labels=statistics_data.label, rotation=20)
        ax.set_xlabel(xlabel=statistics_data.x_label)
        ax.set_ylabel(ylabel=statistics_data.y_label)
        ax.set_title(statistics_data.title + ' in ' + provider)
        ax.tick_params(labelsize=9)
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        plt.legend(loc='upper right', bbox_to_anchor=(1.1255555, 1), ncol=1, borderaxespad=1, shadow=True)
        response = HttpResponse(content_type='image/png')
        canvas = FigureCanvasAgg(fig)
        canvas.print_png(response)
        plt.close()
        return response

    def __get_data(self, provider, institution):
        current_date = get_current_date()
        start_date = get_start_date(end_date=current_date)
        provider_data = ProviderData(provider=provider, institution=institution, end_date=current_date, start_date=start_date)
        return provider_data


class GatherView(TemplateView):
    """gathering storage info."""
    raise_exception = True

    def get(self, request, *args, **kwargs):
        # simple authentication
        access_token = self.kwargs.get('access_token')
        if not simple_auth(access_token):
            response_hash = {'state': 'fail', 'error': 'access forbidden'}
            response_json = json.dumps(response_hash)
            response = HttpResponse(response_json, content_type='application/json')
            return response
        # user
        user = self.request.user
        self.cnt = 0
        self.stat_list = []
        current_date = get_current_date()
        try:
            # create session
            self.session = requests.Session()
            self.adapter = requests.adapters.HTTPAdapter(max_retries=WB_MAX_RETRY)
            # user crawling
            for user in self.get_users():
                if user.affiliated_institutions.first():
                    institution = user.affiliated_institutions.first()
                else:
                    institution = get_dummy_institution()
                cookie = self.get_cookie(user)
                for node in self.get_user_nodes(user):
                    providers = node.get_addon_names()
                    for guid in node.guids.all():
                        for provider in providers:
                            self.count_list = []
                            path = '/'
                            self.count_project_files(node_id=guid._id, provider=provider, path=path, cookies=cookie)
                            if len(self.count_list) > 0:
                                self.regist_database(node=node, guid=guid, owner=user, institution=institution,
                                             provider=provider, date_acquired=current_date, count_list=self.count_list)
                                self.stat_list.append([institution.name, guid._id, provider])
            response_json = json.dumps(self.stat_list)
            response = HttpResponse(response_json, content_type='application/json')
            # statistics mail send
            send_stat_mail(request)
        except Exception as err:
            response_hash = {'state': 'fail', 'error': str(err)}
            response_json = json.dumps(response_hash)
            response = HttpResponse(response_json, content_type='application/json')
            send_error_mail(err)
        finally:
            self.session.close()
        return response

    def regist_database(self, node, guid, owner, institution, provider, date_acquired, count_list):
        """regist count data to database"""
        reg_list = []
        cols = ['type', 'id', 'size', 'ext']
        count_data = pd.DataFrame(count_list, columns=cols)
        number_sum = count_data[count_data['type'] == 'file'].groupby('ext').count()
        ext_sum = count_data[count_data['type'] == 'file'].groupby('ext').sum(numeric_only=True)
        number_sum.fillna(0, inplace=True)
        ext_sum.fillna(0, inplace=True)
        for ext in number_sum.index:
            RdmStatistics.objects.update_or_create(
                project_id=node.id,
                provider=provider,
                extention_type=ext,
                date_acquired=date_acquired.strftime('%Y-%m-%d'),
                defaults={
                    'owner': owner,
                    'institution': institution,
                    'storage_account_id': guid._id,
                    'project_root_path': '/',
                    'subtotal_file_number': number_sum[number_sum.index == ext]['type'].values[0],
                    'subtotal_file_size': ext_sum[ext_sum.index == ext]['size'].values[0],
                },
            )
            reg_list.append([node.id, owner.id, provider, institution.name, ext,
                            number_sum[number_sum.index == ext]['type'].values[0],
                            ext_sum[ext_sum.index == ext]['size'].values[0],
                            date_acquired.strftime('%Y-%m-%d')])
        return reg_list

    def gather(**kwargs):
        """gathering storage data"""

    def get_users(self):
        return OSFUser.objects.all()

    def get_cookie(self, user):
        cookie = user.get_or_create_cookie()
        return cookie

    def get_user_nodes(self, user):
        nodes = AbstractNode.objects.all().select_related().filter(creator_id=user, category='project')
        return nodes


    def get_wb_url(self, path, node_id, provider, cookie):
        url = waterbutler_api_url_for(node_id=node_id, _internal=True, meta=True, provider=provider, path=path, cookie=cookie)
        return url

    def count_project_files(self, node_id, provider, path, cookies):
        """recursive count"""
        url_api = self.get_wb_url(node_id=node_id, provider=provider, path=re.sub(r'^//', '/', path), cookie=cookies)
        self.session.mount('http://', self.adapter)
        headers = {'content-type': 'application/json'}
        # connect timeout:10sec, read timeout:30sec
        res = self.session.get(url=url_api, headers=headers, timeout=(10.0, 30.0))
        if not res.status_code == requests.codes.ok:
            return None
        response_json = res.json()
        self.cnt += 1
        if self.cnt > RECURSIVE_LIMIT:
            return None
        # parse response json
        if 'data' in response_json.keys():
            for obj in response_json['data']:
                if provider != 'osfstorage':
                    root, ext = os.path.splitext(obj['id'])
                else:
                    root, ext = os.path.splitext(obj['attributes']['materialized'])
                if not ext:
                    ext = 'none'
                if obj['attributes']['kind'] == 'file':
                    self.count_list.append(['file', obj['id'], obj['attributes']['size'], ext])
                elif obj['attributes']['kind'] == 'folder':
                    path = re.sub('^' + provider, '', obj['id'])
                    self.count_list.append(['folder', obj['id'], obj['attributes']['size'], ext])
                    self.count_project_files(provider=provider, node_id=node_id, path='/' + path, cookies=cookies)

def simple_auth(access_token):
    digest = hashlib.sha512(SITE_KEY).hexdigest()
    if digest == access_token.lower():
        return True
    else:
        return False

def send_stat_mail(request, **kwargs):
    """統計情報メール送信"""
    current_date = get_current_date()
    all_institutions = Institution.objects.order_by('id').all()
    all_staff_users = OSFUser.objects.filter(is_staff=True)
    response_hash = {}
    for institution in all_institutions:
        # to list
        to_list = []
        for user in all_staff_users:
            if user.is_affiliated_with_institution(institution):
                to_list.append(user.username)
        if not to_list:
            continue
        # cc list
        all_superusers_list = list(OSFUser.objects.filter(is_superuser=True).values_list('username', flat=True))
        cc_list = all_superusers_list
        # cc_list = [] # debug
        set_superusers = set(cc_list) - set(to_list)
        cc_list = list(set_superusers)
        attachment_file_name = 'statistics' + current_date.strftime('%Y%m%d') + '.pdf'
        attachment_file_data = get_pdf_data(institution=institution)
        mail_data = {
            'subject': '[[GakuNin RDM]] [[' + institution.name + ']] statistic information at ' + current_date.strftime('%Y/%m/%d'),
            'content': 'statistic information of storage in ' + institution.name + ' at ' + current_date.strftime('%Y/%m/%d') + '\r\n\r\n' +
            'This mail is automatically delivered from GakuNin RDM.\r\n*Please do not reply to this email.\r\n',
            'attach_file': attachment_file_name,
            'attach_data': attachment_file_data
        }
        response_hash[institution.name] = send_email(to_list=to_list, cc_list=cc_list, data=mail_data, user=user)
    response_json = json.dumps(response_hash)
    response = HttpResponse(response_json, content_type='application/json')
    return response

def send_error_mail(err):
    """エラーメール送信"""
    current_date = get_current_date()
    # to list
    all_superusers_list = list(OSFUser.objects.filter(is_superuser=True).values_list('username', flat=True))
    to_list = all_superusers_list
    mail_data = {
        'subject': '[[GakuNin RDM]] ERROR in statistic information collection at ' + current_date.strftime('%Y/%m/%d'),
        'content': 'ERROR OCCURED at ' + current_date.strftime('%Y/%m/%d') + '.\r\nERROR: \r\n' + str(err),
    }
    send_email(to_list=to_list, cc_list=None, data=mail_data)
    response_hash = {'state': 'fail', 'error': str(err)}
    response_json = json.dumps(response_hash)
    response = HttpResponse(response_json, content_type='application/json')
    return response

def send_email(to_list, cc_list, data, user, backend='smtp'):
    """send email to administrator"""
    ret = {'is_success': True, 'error': ''}
    try:
        if backend == 'smtp':
            connection = mail.get_connection(backend='django.core.mail.backends.smtp.EmailBackend')
        else:
            connection = mail.get_connection(backend='django.core.mail.backends.console.EmailBackend')
        message = EmailMessage(
            data['subject'],
            data['content'],
            from_email=SUPPORT_EMAIL or user.username,
            to=to_list,
            cc=cc_list
        )
        if 'attach_data' in data:
            message.attach(data['attach_file'], data['attach_data'], 'application/pdf')
        message.send()
        connection.send_messages([message])
        connection.close()
    except Exception as e:
        ret['is_success'] = False
        ret['error'] = 'Email error: ' + str(e)
    finally:
        return ret

def get_pdf_data(institution):
    current_date = get_current_date()
    start_date = get_start_date(end_date=current_date)
    provider_data_array = get_provider_data_array(institution=institution, start_date=start_date, end_date=current_date)
    template_name = 'rdm_statistics/statistics_report.html'
    # context data
    ctx = {}
    if institution:
        ctx['institution'] = institution
    ctx['current_date'] = current_date
    ctx['provider_data_array'] = provider_data_array
    html_string = render_to_string(template_name, ctx)
    # if PDF
    converted_pdf = convert_to_pdf(html_string=html_string, file=False)
    return converted_pdf

def get_current_date(is_str=False):
    current_datetime = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
    current_date = datetime.date(current_datetime.year, current_datetime.month, current_datetime.day)
    if is_str:
        return current_datetime.strftime('%Y/%m/%d')
    else:
        return current_date

class SendView(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    """index view of statistics module."""
    template_name = 'rdm_statistics/mail.html'
    raise_exception = True

    def test_func(self):
        """validate user permissions"""
        institution_id = int(self.kwargs.get('institution_id'))
        if not self.is_authenticated:
            return False
        if self.is_super_admin or self.is_admin:
            return self.has_auth(institution_id)
        return False

    def get_context_data(self, **kwargs):
        """get contexts"""
        ret = {'is_success': True, 'error': ''}
        ctx = super(SendView, self).get_context_data(**kwargs)
        user = self.request.user
        institution_id = int(kwargs['institution_id'])
        if Institution.objects.filter(pk=institution_id).exists():
            institution = Institution.objects.get(pk=institution_id)
        else:
            institution = get_dummy_institution()
        all_superusers_list = list(OSFUser.objects.filter(is_superuser=True).values_list('username', flat=True))
        to_list = [user.username]
        cc_list = all_superusers_list
        if user.is_superuser:
            cc_list.remove(user.username)
        elif not user.is_staff:
            ret['is_success'] = False
            return ctx
        current_date = get_current_date()
        attachment_file_name = 'statistics' + current_date.strftime('%Y/%m/%d') + '.pdf'
        attachment_file_data = get_pdf_data(institution=institution)
        mail_data = {
            'subject': '[[GakuNin RDM]] statistic information at ' + current_date.strftime('%Y/%m/%d'),
            'content': 'statistic information of storage in ' + institution.name + ' at ' + current_date.strftime('%Y/%m/%d'),
            'attach_file': attachment_file_name,
            'attach_data': attachment_file_data
        }
        ret = send_email(to_list=to_list, cc_list=cc_list, data=mail_data, user=user)
        data = {
            'ret': ret,
            'mail_data': mail_data
        }
        ctx['data'] = data
        return ctx


SUFFIXES = {1000: ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
            1024: ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']}

def approximate_size(size, a_kilobyte_is_1024_bytes=True):
    """Convert a file size to human-readable form.

    Keyword arguments:
    size -- file size in bytes
    a_kilobyte_is_1024_bytes -- if True (default), use multiples of 1024
                                if False, use multiples of 1000

    Returns: string

    """
    if size < 0:
        raise ValueError('number must be non-negative')

    multiple = 1024 if a_kilobyte_is_1024_bytes else 1000
    if size < multiple:
        return '{0:.1f} {1}'.format(size, 'B')
    for suffix in SUFFIXES[multiple]:
        size /= multiple
        if size < multiple:
            return '{0:.1f} {1}'.format(size, suffix)

    raise ValueError('number too large')


############################################
### views or funcs for development and test
############################################

class IndexView(TemplateView):
    """index view of statistics module."""
    template_name = 'rdm_statistics/index.html'
    raise_exception = True

    def find_bookmark_collection(self, user):
        collection = apps.get_model('osf.Collection')
        return collection.objects.get(creator=user, is_deleted=False, is_bookmark_collection=True)

    def get(self, request, *args, **kwargs):
        user = self.request.user
        user_addons = utils.get_addons_by_config_type('users', self.request.user)
        accounts_addons = [addon for addon in website_settings.ADDONS_AVAILABLE
                           if 'accounts' in addon.configs]
        js = []
        bookmark_collection = self.find_bookmark_collection(user)
        my_projects_id = bookmark_collection._id
        nodes = AbstractNode.objects.all().select_related().filter(creator_id=user, category='project')
        data = {
            'test': 'test',
            'user': user,
            'addon': user_addons,
            'accounts_addons': accounts_addons,
            'js': js,
            'my_project_id': my_projects_id,
            'bookmark collection': bookmark_collection,
            'node': nodes
        }
        ctx = {
            'data': data
        }

        return self.render_to_response(ctx)


class DummyCreateView(RdmPermissionMixin, UserPassesTestMixin, TemplateView):
    """simulate data collecting."""
    template_name = 'rdm_statistics/index.html'
    raise_exception = True

    def test_func(self):
        """権限等のチェック"""
        institution_id = int(self.kwargs.get('institution_id'))
        return self.has_auth(institution_id)

    def get_context_data(self, **kwargs):
        """コンテキスト取得"""
        ctx = super(DummyCreateView, self).get_context_data(**kwargs)
        user = self.request.user
        institution_id = int(kwargs['institution_id'])
        institution = Institution.objects.get(pk=institution_id)
        current_date = get_current_date()
        result = self.insert_data(user=user, institution=institution)
        data = {
            'current date': current_date,
            'data': result
        }
        ctx['data'] = data
        return ctx

    def insert_data(self, **kwargs):
        """get data"""
        user = kwargs['user']
        institution = kwargs['institution']
        user = kwargs['user']
        # for test data
        accounts_addons = [addon for addon in website_settings.ADDONS_AVAILABLE
                           if 'accounts' in addon.configs]
        addon_list = [addon.short_name for addon in accounts_addons]
        provider_list = np.random.choice(addon_list, 3, replace=False)
        TEST_TIMES = 2
        TEST_RANGE = RANGE_STATISTICS * TEST_TIMES
        RdmStatistics.objects.filter(institution=institution).delete()
        for provider in provider_list:
            current_date = get_current_date()
            ext_list = ['jpg', 'png', 'docx', 'xlsx']
            for ext_type in ext_list:
                x = np.random.randint(1000 * TEST_RANGE / 10, size=TEST_RANGE)
                y = np.random.randint(100 * TEST_RANGE / 10, size=TEST_RANGE)
                count_list = np.sort(y)
                size_list = np.sort(x)
                for i in range(TEST_RANGE):
                    date = current_date - datetime.timedelta(weeks=(TEST_RANGE - 1 - i))
                    RdmStatistics.objects.create(project_id=7,
                                                 owner=user,
                                                 institution=institution,
                                                 provider=provider,
                                                 storage_account_id='aaa',
                                                 project_root_path='/',
                                                 sextention_type=ext_type,
                                                 subtotal_file_number=count_list[i],
                                                 subtotal_file_size=size_list[i],
                                                 date_acquired=date)
        return RdmStatistics.objects.all()

def test_mail(request, status=None):
    """send email test """
    ret = {'is_success': True, 'error': ''}
    # to list
    all_superusers_list = list(OSFUser.objects.filter(is_superuser=True).values_list('username', flat=True))
    to_list = all_superusers_list
    cc_list = []
    # attachment file
    current_date = datetime.datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y/%m/%d %H:%M:%S')
    subject = 'test mail : ' + current_date
    content = 'test regular mail sending'
    try:
        connection = mail.get_connection(backend='django.core.mail.backends.smtp.EmailBackend')
        message = EmailMessage(
            subject,
            content,
            from_email=SUPPORT_EMAIL,
            to=to_list,
            cc=cc_list
        )
        message.send()
        connection.send_messages([message])
        connection.close()
    except Exception as e:
        ret['is_success'] = False
        ret['error'] = 'Email error: ' + str(e)
    json_str = json.dumps(ret)
    response = HttpResponse(json_str, content_type='application/javascript; charset=UTF-8', status=status)
    return response
