import os
import re
import hmac
import json
import uuid
import hashlib
import logging
import urlparse
import httplib as http
from nameparser import HumanName
import functools
from collections import OrderedDict

from framework import Q
from framework.forms.utils import sanitize
from framework.exceptions import HTTPError
from framework.flask import request
from framework.auth.decorators import Auth

from website import settings, security
from website.util import web_url_for
from website.models import User, Node, MailRecord
from website.project import new_node
from website.project.views.file import prepare_file
from website.util.sanitize import deep_clean

from website import settings

logger = logging.getLogger(__name__)

def must_have_valid_signature(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
    
        sent_signature = request.json.get('signature')
        payload = request.json.get('project')        
        payload = OrderedDict(sorted(payload.items(), key=lambda t: t[0]))
        signature_is_valid = None

        import pdb; pdb.set_trace()
        signature = hmac.new(
            key=settings.OSF_API_KEY,
            msg=json.dumps(payload),
            digestmod=hashlib.sha256,
        ).hexdigest()

        signature_is_valid = (sent_signature == signature)
       
        if signature_is_valid:
            return func(*args, **kwargs)
        else:
            print signature
            print sent_signature
            raise HTTPError(http.NOT_ACCEPTABLE)         
    return wrapped

def get_or_create_user(fullname, address, sys_tags=[]):
    """Get or create user by email address.
    """
    user = User.find(Q('username', 'iexact', address))
    user = user[0] if user.count() else None
    user_created = False
    if user is None:
        password = str(uuid.uuid4())
        user = User.create_confirmed(address, password, fullname)
        user.verification_key = security.random_string(20)
        # Flag as potential spam account if Mailgun detected spam
        if sys_tags and len(sys_tags) > 0:
            for tag in sys_tags:
                user.system_tags.append(tag)
        user.save()
        user_created = True

    return user, user_created

@must_have_valid_signature
def import_project():
    errors = []    

    project_data = request.json.get('project')
    if not project_data:
        errors.append({'error': 'No project data submitted'})

    contributors = project_data['contributors']
    for i in range(len(contributors)):        
        contributor = contributors[i]
        name = contributor['full_name'] or contributor['last_name'] or contributor['email'].split('@')[0]
        contributors[i] = get_or_create_user(name, contributor['email']) #TODO add sys_tags

    auth = Auth(user=contributors[0][0])

    title = project_data['title']
    nodes = []
    
    project = new_node('project', title, contributors[0])
    nodes = [project]
    project.set_privacy('public', auth=auth)

    # update project description
    description = project_data['description']
    project.update_node_wiki(
        page='home',
        content=sanitize(description),
        auth=auth,            
    )

    # add tags
    tags = project_data['tags'] or []
    for tag in tags:           
        project.add_tag(tag, auth=auth)
    '''
    system_tags = [project_data['source'],'imported']
    for tag in system_tags:
        if tag not in project['system_tags']:
            project['system_tags'].append(tag)
    '''
    # add components        
    components = project_data.get('components') or []
    for component in components:
        comp = new_node('component', component['title'], contributors[0], description=component['description'], project=project)
        nodes.append(comp)

    for contributor in contributors:
        for node in nodes:
            node.add_contributor(contributor[0], auth=auth)
            node.save()

