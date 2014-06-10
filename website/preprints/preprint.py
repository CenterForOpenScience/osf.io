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
def upload_preprint_new(**kwargs):
    # todo: lots of duplication from upload_preprint here
    # todo: validation that file is pdf
    auth = kwargs['auth']
    file = request.files.get('file')
    title = splitext(file.filename)[0]
    file.filename = u'preprint.pdf'

    description = 'Automatically generated as a preprint for ' + title
    project = new_node('project', title, auth.user, description=description)
    project.set_privacy('private', auth=auth)


    project.save()

    preprint_component = new_node('preprint', title + " Preprint", auth.user, project=project)
    preprint_component.set_privacy('public', auth=auth)
    preprint_component.save()


    file_name, file_content, file_content_type, file_size = prepare_file(file)
    preprint_component.add_file(
        auth=auth,
        file_name=file_name,
        content=file_content,
        size=file_size,
        content_type=file_content_type,
    )

    return redirect(preprint_component.url+'preprint/')

@must_be_valid_project
def upload_preprint(**kwargs):
    #todo: This is wholesale copied from add_file_to_node with different permissions stuff. fix that.
    rv = osffiles_views.upload_file_public(filename="preprint.pdf", **kwargs)
    kwargs['node'].save()
    return rv