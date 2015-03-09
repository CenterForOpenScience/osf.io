def datetime_to_csl(dt):
    """Given a datetime, return a dict in CSL-JSON date-variable schema"""
    return {'date-parts': [[dt.year, dt.month, dt.day]]}