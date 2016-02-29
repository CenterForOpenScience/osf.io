"""
Metrics scripts
"""
from datetime import datetime
from website.project.model import User

from .models import OSFStatistic


def osf_site():
    statistic = OSFStatistic(date=datetime.utcnow())
    statistic.users = User.find().count()
    statistic.save()
