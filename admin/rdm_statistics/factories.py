# -*- coding: utf-8 -*-

from factory import SubFactory
from factory.django import DjangoModelFactory
from osf import models
from osf_tests.factories import InstitutionFactory


class RdmAddonOptionFactory(DjangoModelFactory):
    provider = 's3'
    institution = SubFactory(InstitutionFactory)
    class Meta:
        model = models.RdmAddonOption

class RdmAddonNoInstitutionFactoryOption(DjangoModelFactory):
    provider = 's3'
    class Meta:
        model = models.RdmAddonNoInstitutionOption
