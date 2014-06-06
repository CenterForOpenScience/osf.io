import httplib as http
from flask import request
from framework import must_be_logged_in
from website.project import new_node
from website.project.utils import prepare_file
from os.path import basename

@must_be_logged_in
def preprint_new(**kwargs):
    return {}, http.OK


@must_be_logged_in
def upload_preprint_new(**kwargs):
    # todo: lots of duplication from upload_preprint here
    # todo: validation that file is pdf
    auth = kwargs['auth']
    file = request.files.get('file')
    title = basename(file.filename)
    file.filename = u'preprint.pdf'

    description = 'Automatically generated as a preprint for ' + title
    project = new_node('project', title, auth.user, description=description)
    project.set_privacy('private', auth=auth)


    project.save()

    preprint_component = new_node('preprint', title, auth.user, project=project)
    preprint_component.save()


    file_name, file_content, file_content_type, file_size = prepare_file(file)
    preprint_component.add_file(
        auth=auth,
        file_name=file_name,
        content=file_content,
        size=file_size,
        content_type=file_content_type,
    )

    return {"url": preprint_component.url+'preprint/'}, 201, None, preprint_component.url+'preprint/'