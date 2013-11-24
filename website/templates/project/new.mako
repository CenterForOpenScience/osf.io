<%inherit file="base.mako"/>
<%def name="title()">Create New Project</%def>
<%def name="content()">
<h2 class="page-title text-center">Create New Project</h2>
<div class="row">
    <div class="col-md-6 col-md-offset-3">
        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/new_project/",
                "kwargs": {
                    "name": "newProject",
                    "method_string": "POST",
                    "action_string": "/project/new/",
                    "form_class": "form-stacked",
                    "submit_string": "Create New Project",
                    "id": "projectForm",
                    "submit_btn_class": "btn-primary"
                },
                "replace": true
            }'>
        </div>
    </div>
</div><!-- end row -->
</%def>
