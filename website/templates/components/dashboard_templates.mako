## A reuseable OSF project typeahead search widget. Uses the custom projectSearch binding handler.
<template id="osf-project-search">
<form data-bind="submit: onSubmit">
    <div class="ob-search">
        <!-- Project search typeahead -->
        <div data-bind="css: {'has-success': hasSelectedProject()}" class="form-group ob-input">
            <img
                data-bind="click: clearSearch, visible: hasSelectedProject()"
                class="ob-clear-button pull-right" src="/static/img/close2.png" alt="Clear search">
            <input
            data-bind="projectSearch: {
                            data: data,
                            onSelected: onSelectedProject
                        },
                        value: projectInput,
                        attr: {readonly: hasSelectedProject(),
                            placeholder: projectPlaceholder}"
                class="typeahead ob-typeahead-input form-control"
                name="project"
                type="text"
                placeholder=>
        </div><!-- end .form-group -->

        <!-- Component search typeahead -->
        <!-- ko if: enableComponents && showComponents && hasSelectedProject() -->
        <div data-bind="css: {'has-success': hasSelectedComponent()}" class="form-group ob-input">
            <img
                data-bind="click: clearComponentSearch, visible: hasSelectedComponent()"
                class="ob-clear-button pull-right" src="/static/img/close2.png" alt="Clear search">
            <input
            data-bind="projectSearch: {
                            data: componentURL,
                            onSelected: onSelectedComponent,
                            onFetched: onFetchedComponents,
                            clearOn: cleared
                        },
                    value: componentInput,
                    attr: {readonly: hasSelectedComponent(),
                            placeholder: componentPlaceholder}"
                class="typeahead ob-typeahead-input form-control"
                name="component"
                type="text"
                >
        </div><!-- end .form-group -->
        <!-- /ko -->
    </div> <!-- end .ob-search -->
    <button type="submit" data-bind="visible: showSubmit(), html: submitText"
            class="btn btn-primary pull-right" >
    </button>
</form>
</template>

## The onboarding "register" widget
<template id="osf-ob-register">
<div class="m-b-sm panel panel-default ob-list-item">
    <div data-bind="click: toggle" class="panel-heading clearfix pointer">
        <h3 class="m-xs panel-title">Register a project</h3>
        <div class="pull-right" >
            <a href="#" class="btn btn-sm project-toggle"><i class="fa fa-angle-down"></i></a>
        </div>
    </div><!-- end ob-header -->

    <div style="display:none;" class="panel-body">
        <div class="row">
            <div class="col-md-12" >
                <osf-project-search
                params="data: data,
                        onSubmit: onRegisterSubmit,
                        enableComponents: false,
                        submitText: 'Continue registration...'">
                </osf-project-search>
            </div><!-- end col-md -->
        </div><!-- end row -->
    </div>
</div> <!-- end .ob-list -->
</template>

<template id="osf-ob-create">
    <div id="obNewProject" class=" panel panel-default m-b-sm ob-list-item">
        <div class="panel-heading clearfix pointer">
            <h3 class="m-xs panel-title">Create a project</h3>
           <div class="pull-right" >
                <a href="#" class="btn btn-sm project-toggle"><i class="fa fa-angle-down"></i></a>
           </div>
        </div><!-- end ob-header -->
        <div style="display:none" class="panel-body" id="obRevealNewProject">
            <osf-project-create-form
                params="data: nodes, hasFocus: focus">
            </osf-project-create-form>
        </div>
    </div> <!-- end ob-list-item -->
</template>


<template id="osf-ob-uploader">
<div class="m-b-sm panel panel-default ob-list-item">
    <div class="pointer panel-heading clearfix ">
        <h3 class="m-xs panel-title">Upload file(s)</h3>
        <div class="pull-right" >
            <a href="#" class="btn btn-sm project-toggle"><i class="fa fa-angle-up"></i></a>
        </div>
    </div><!-- end ob-header -->


    <div class="panel-body">
        <div class="row">
            <div class="col-md-12">
                <h4>1. Drop file (or click below)</h4>

                <!-- Dropzone -->
                <div data-bind="click: clearMessages(), visible: enableUpload()" id="obDropzone" class="osf-box box-round osf-box-lt ob-dropzone ob-dropzone-box osf-box box-round box-lt pull-left"></div>

                <!-- File queue display -->
                <div data-bind="visible: !enableUpload()" class="ob-dropzone-selected ob-dropzone-box osf-box box-round box-lt pull-left">
                    <img data-bind="attr: {src: iconSrc()}" class="ob-dropzone-icon m-t-sm" alt="File icon">
                    <div data-bind="text: filename" class="m-t-sm"></div>
                    <progress
                        data-bind="attr: {value: progress()}, visible: showProgress()"
                            class="ob-upload-progress" max="100"></progress>
                    <img data-bind="click: clearDropzone"
                        class="ob-clear-uploads-button pull-right" src="/static/img/close2.png" alt="Clear uploads">
                </div>

            </div><!-- end col-md -->
        </div><!-- end row -->
        <div class="row">
            <div class="col-md-12">
                <h4> 2. Select a project</h4>
                <osf-project-search
                params="data: data,
                        onSubmit: startUpload,
                        onClear: clearMessages,
                        onSelected: clearMessages,
                        submitText: 'Upload'">
                </osf-project-search>
            </div>
        </div><!-- end row -->
        <div data-bind="html: message(), attr: {class: messageClass()}" ></div>
    </div>
</div> <!-- end .ob-list -->
</template>

<template id="osf-project-create-form">
<form id="creationForm" data-bind="submit: submitForm">
    ## Uncomment for debugging
    <div class="row">
        <div class="col-md-12">
            <label for="title">Title</label>
            <input class="form-control"
                type="text" name="title"
                maxlength="200"
                data-bind="value: title, valueUpdate:'input', hasFocus: focus"
                >

            <!-- flashed validation message -->
            <span class="text-danger" data-bind="text: errorMessage"></span>
            <br />
            
##            <label>Category </label>
##            <select class="form-control"
##                    data-bind="value: category,
##                               options: categories,
##                               optionsText: function(val) { return categoryMap[val]}">
##            </select>
##            <br />

            <label>Description (Optional)</label>
            <textarea data-bind="value: description"class="form-control resize-vertical" name="description"
                ></textarea>
            <br />
            <label>Template (Optional)</label>
            <span class="help-block">Start typing to search. Selecting project as template will duplicate its structure in the new project without importing the content of that project.</span>
            <input type="hidden" class="select2-container create-node-templates" id="createNodeTemplatesInput" style="width: 100%">
        </div>
    </div>
    <br />
    <div class="row">
        <div class="col-md-12">
            <button data-bind="enable: enableCreateBtn" class="btn btn-primary pull-right" type="submit">Create</button>
        </div>
    </div>
</form>
</template>

<template id="osf-ob-goto">
<div class="panel panel-default m-b-sm ob-list-item">
    <div class="panel-heading clearfix pointer">
        <h3 class="panel-title">Go to my project</h3>
        <div class="pull-right" >
            <a href="#" class="btn btn-sm project-toggle"><i class="fa fa-angle-up"></i></a>
        </div>
    </div><!-- end ob-header -->
    <div class="row panel-body">
        <div>
            <div class="col-md-12" >

                <!-- ko if: data.length -->
                <osf-project-search
                params="data: data,
                        onSubmit: onSubmit,
                        submitText: submitText,
                        projectPlaceholder: 'Start typing a project name'">
                </osf-project-search>
                <!-- /ko -->
                <!-- ko if: !data.length -->
                <p class="text-info">
                    You do not have any projects yet. Click below to create one!
                </p>
                <!-- /ko -->
            </div><!-- end col-md -->
        </div>
    </div><!-- end row -->
</div> <!-- end .ob-list -->
</template>
