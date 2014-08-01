<%inherit file="base.mako"/>
<%def name="title()">Create New Project</%def>
<%def name="content()">
<h2 class="page-title text-center">Create New Project</h2>
<!--<div class="row">
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
</div>
-->
<div class="row" id="creation-form">
  <div class="col-md-6 col-md-offset-3">
    <label for="title">Title</label>
    <input class="form-control" type="text" data-bind="value: title">
    <br />
    <label>Description</label>
    <textarea class="form-control" data-bind="value: description"></textarea>
    <br />
    <label>Template</label>
    <span class="help-block">Start typing to search. Selecting project as
      template will duplicate its structure in the new project without importing the
      content of that project.</span>
    <input class="form-control" type="text">
    <br>
    <button class="btn btn-primary" data-bind="click: createProject">Create New Project</button>
  </div>
</div>

</%def>

<%def name="stylesheets()">
<link rel="stylesheet" href="/static/vendor/bower_components/jquery-ui/themes/base/jquery-ui.css">
</%def>

<%def name="javascript_bottom()">
<script>
  $script('/static/js/projectCreator.js', function() {
    ProjectCreator('#creation-form', 'url');
  });
    // TODO(sloria): require('jquery') here
    //block the create new project button when the form is submitted
    $('#projectForm').on('submit',function(){
        $('button[type="submit"]', this)
            .attr('disabled', 'disabled')
            .text('Creating');
    });
</script>
</%def>
