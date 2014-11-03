<%inherit file="base.mako"/>
<%def name="title()">Create New Project</%def>
<%def name="content()">
<h2 class="page-title text-center">Create New Project</h2>

<form id="creationForm" data-bind="submit: submitForm">

    ## Uncomment for debugging
    ## <pre data-bind="text: ko.utils.stringifyJson($data, null, 2)"></pre >
    <div class="row">
        <div class="col-md-6 col-md-offset-3">
            <label for="title">Title</label>
            <input class="form-control" type="text" name="title" data-bind="value: title, valueUpdate:'input'" placeholder="Required">

            <!-- flashed validation message -->
            <span class="text-danger" data-bind="text: errorMessage"></span>
            </br>

            <label>Description</label>
            <textarea class="form-control" name="description" data-bind="value: description"></textarea>
            <br />
            <label>Template</label>
            <span class="help-block">Start typing to search. Selecting project as template will duplicate its structure in the new project without importing the content of that project.</span>
            <input type="hidden" id="templates" class="select2-container" style="width: 100%">
        </div>
    </div>
    <br />
    <div class="row">
        <div class="col-md-6 col-md-offset-3">
            <button class="btn btn-primary" type="submit" data-bind="enable: title.isValid()" disabled>Create New Project</button>
        </div>
    </div>
</form>


</%def>

<%def name="stylesheets()">
<link rel="stylesheet" href="/static/vendor/bower_components/select2/select2.css">
</%def>

<%def name="javascript_bottom()">
<script>
    $script(['/static/js/projectCreator.js', '/static/vendor/bower_components/select2/select2.js'], function() {
        ProjectCreator('#creationForm', '/api/v1/project/new/');
    });
</script>
</%def>
