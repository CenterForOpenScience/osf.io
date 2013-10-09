<%inherit file="contentContainer.mako" />

<h2>Create New Project</h2>
<div mod-meta='{
        "tpl": "util/render_form.mako",
        "uri": "/api/v1/forms/new_project/",
        "kwargs": {
            "name": "newProject",
            "method_string": "POST",
            "action_string": "/api/v1/project/new/",
            "form_class": "form-stacked",
            "submit_string": "Create New Project"
        },
        "replace": true
    }'>
</div>