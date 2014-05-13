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

<%def name="stylesheets()">
<link rel="stylesheet" href="/static/vendor/bower_components/jquery-ui/themes/base/jquery-ui.css">
</%def>

<%def name="javascript_bottom()">
<script>
    // TODO(sloria): require('jquery') here
    //block the create new project button when the form is submitted
    $('#projectForm').on('submit',function(){
        $('button[type="submit"]', this)
            .attr('disabled', 'disabled')
            .text('Creating');
    });
</script>
</%def>
