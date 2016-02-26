"""
Metrics scripts
"""
from website.project.model import User

from .models import OSFStatistic


def osf_site():
    statistic = OSFStatistic()
    statistic.users = User.find().count()
    statistic.save()
