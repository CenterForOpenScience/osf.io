"""
Metrics scripts
"""
from datetime import datetime, timedelta
from modularodm import Q
from website.project.model import User

from .models import OSFStatistic


def osf_site():
    current_time = datetime.utcnow()
    midnight = current_time - timedelta(
        hours=current_time.hour,
        minutes=current_time.minute
    )
    statistic = OSFStatistic(date=current_time)
    query = Q('date_registered', 'lt', midnight)
    statistic.users = User.find(query).count()
    statistic.save()
