# -*- coding: utf-8 -*-
import framework
from . import rubeus



def api_url_for(view_name, *args, **kwargs):
    return framework.url_for('JSONRenderer__{0}'.format(view_name),
        *args, **kwargs)


def web_url_for(view_name, *args, **kwargs):
    return framework.url_for('OsfWebRenderer__{0}'.format(view_name),
        *args, **kwargs)
