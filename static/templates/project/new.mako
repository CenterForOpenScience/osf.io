<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>

<h2>Create New Project</h2>
<div mod-meta='{
        "tpl": "util/render_form.mako",
        "uri": "/api/v1/forms/new_project/",
        "kwargs": {
            "name": "newProject",
            "method_string": "POST",
            "action_string": "/project/new/",
            "form_class": "form-stacked",
            "submit_string": "Create New Project"
        },
        "replace": true
    }'>
</div>

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>