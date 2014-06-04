import os
import re
import hmac
import json
import uuid
import hashlib
import logging
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
from website.models import User, Node
from website.project import new_node
from website.project.views.file import prepare_file
from website.util.sanitize import deep_clean
from website.project.decorators import must_be_valid_project, must_have_valid_signature
from website import settings

logger = logging.getLogger(__name__)

# TODO move this somewhere better
# maybe website/project/views/user or website/project/models
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
        if sys_tags and len(sys_tags) > 0:
            for tag in sys_tags:
                user.system_tags.append(tag)
        user.save()
        user_created = True

    return user, user_created

@must_have_valid_signature
def import_projects(**kwargs):
    project_data = deep_clean(request.json)
    if not project_data:
        return {'error': 'No project data submitted'}
    
    if not isinstance(project_data, list):
        project_data = [project_data]
    for entry in project_data:                    
        contributors = entry['contributors']
        
        for i in range(len(contributors)):        
            contributor = contributors[i]
            name = contributor['full_name'] or contributor['last_name'] or contributor.get('email').split('@')[0]
            email = contributor.get('email') or ''
            contributors[i], created = get_or_create_user(name, email) #TODO add sys_tags

        auth = Auth(user=contributors[0])

        title = entry['title']
        nodes = []

        project = new_node('project', title, contributors[0])
        nodes = [project]
        project.set_privacy('public', auth=auth)

        # update project description
        description = entry['description']
        project.update_node_wiki(
            page='home',
            content=sanitize(description),
            auth=auth,            
        )

        # add tags
        tags = entry['tags'] or []
        for tag in tags:           
            project.add_tag(tag, auth=auth)

        system_tags = [entry['imported_from'],'imported']
        for tag in system_tags:
            if tag not in project.system_tags:
                project.system_tags.append(tag)

        project.save()
        # add components        
        components = entry.get('components') or []
        for i in range(len(components)):
            component = components[i]
            comp = new_node('component', component['title'], contributors[0], description=component['description'], project=project)
            components[i] = comp
            nodes.append(comp)

        for contributor in contributors[1:]:
            for node in nodes:
                import pdb;pdb.set_trace()
                node.add_contributor(contributor, auth=auth)
                node.save()

        return {
            "project": {
                "title": project.title,
                "id": project._id,
                "components": [
                    {
                        "title": c.title,
                        "id": c._id,
                    } for c in components]
            }
        }

