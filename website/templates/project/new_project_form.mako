<form id="creationForm" data-bind="submit: submitForm">

    ## Uncomment for debugging
    ## <pre data-bind="text: ko.utils.stringifyJson($data, null, 2)"></pre >
    <div class="row">
        <div class="col-md-12">
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
        <div class="col-md-12">
            <button class="btn btn-primary pull-right" type="submit" data-bind="enable: title.isValid()" disabled>Create</button>
        </div>
    </div>
</form>



<link rel="stylesheet" href="/static/vendor/bower_components/select2/select2.css">

<script>
    $script(['/static/js/projectCreator.js']);  // exports projectCreator
    $script.ready('projectCreator', function() {
        ProjectCreator('#creationForm', '/api/v1/project/new/');
    });
</script>
