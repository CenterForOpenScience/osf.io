# -*- coding: utf-8 -*-

from factory import SubFactory
from factory.django import DjangoModelFactory
from osf import models
from osf_tests.factories import ProjectFactory
import datetime

class RdmStatisticsFactory(DjangoModelFactory):
    class Meta:
        model = models.RdmStatistics

    project_root_path = '/'
    extention_type = 'png'
    subtotal_file_number = 10
    subtotal_file_size = 1000
    date_acquired = datetime.date.today() - datetime.timedelta(days=(1))
    project = SubFactory(ProjectFactory)
    storage_account_id = 'factory'
