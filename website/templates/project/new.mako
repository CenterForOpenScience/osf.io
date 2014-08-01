<%inherit file="base.mako"/>
<%def name="title()">Create New Project</%def>
<%def name="content()">
<h2 class="page-title text-center">Create New Project</h2>

<div id="creation-form">
  <div class="row">
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
      <input type="hidden" id="templates" class="select2-container" style="width: 100%">
     <!-- <select id="templates" class="select2-container" style="width: 100%">
        <option></option>
        <optgroup label="Your Projects" data-bind="foreach: templates">
          <option data-bind="value: id">{{title}}</option>
        </optgroup>
        <optgroup data-bind="foreach: otherTemplates">
          <option data-bind="value: id">{{title}}</option>
        </optgroup>
      </select>-->
    </div>
  </div>
  <br />
  <div class="row">
    <div class="col-md-6 col-md-offset-3">
      <button class="btn btn-primary" data-bind="click: createProject">Create New Project</button>
    </div>
  </div>
</div>

</%def>

<%def name="stylesheets()">
<link rel="stylesheet" href="/static/vendor/bower_components/jquery-ui/themes/base/jquery-ui.css">
<link rel="stylesheet" href="/static/vendor/bower_components/select2/select2.css">
</%def>

<%def name="javascript_bottom()">
<script>
  $script(['/static/js/projectCreator.js', '/static/vendor/bower_components/select2/select2.js'], function() {
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
