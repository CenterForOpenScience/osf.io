import httplib as http
from flask import request
from framework import must_be_logged_in, redirect
from framework.auth.decorators import Auth
from framework.exceptions import HTTPError
import website.addons.osffiles.views as osffiles_views
from website.project import new_node
from website.project.decorators import must_be_contributor, must_be_valid_project
from os.path import splitext
from website.project.views.file import prepare_file


@must_be_logged_in
def preprint_new(**kwargs):
    return {}, http.OK


@must_be_logged_in
def post_preprint_new(**kwargs):
    # todo: validation that file is pdf
    # todo: add error handling

    auth = kwargs['auth']
    file = request.files.get('file')
    # todo: should this leave it as unicode? Thinking about, e.g. mathematical symbols in titles
    node_title = str(splitext(file.filename)[0])
    file.filename = u'preprint.pdf'

    # creates private project to house the preprint component
    project = new_node('project',
                       node_title,
                       auth.user,
                       description='Automatically generated as a preprint for ' + node_title)
    project.set_privacy('private', auth=auth)

    # creates public component to house the preprint file
    preprint_component = new_node('preprint',
                                  node_title + " (Preprint)",
                                  auth.user,
                                  project=project)
    preprint_component.set_privacy('public', auth=auth)

    # adds file to new component
    upload_preprint(project=project,
                    node=preprint_component,
                    # save=False, # for now, saving upon creation. rewrite to save at the end
                    **kwargs)

    # commits to database upon successful creation of everything
    project.save()
    preprint_component.save()

    return redirect(preprint_component.url+'preprint/')

@must_be_valid_project
def upload_preprint(save=True, **kwargs):
    #todo: This is wholesale copied from add_file_to_node with different permissions stuff. fix that.
    rv = osffiles_views.upload_file_public(filename="preprint.pdf", **kwargs)
    if save:
        kwargs['node'].save()
    return rv