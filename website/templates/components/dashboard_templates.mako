## A reuseable OSF project typeahead search widget. Uses the custom projectSearch binding handler.
<template id="osf-project-search">
<form data-bind="submit: onSubmit">
    <div class="ob-search">
        <!-- Project search typeahead -->
        <div data-bind="css: {'has-success': hasSelectedProject()}" class="form-group">
            <img
                data-bind="click: clearSearch, visible: hasSelectedProject()"
                class="ob-clear-button pull-right" src="/static/img/close2.png" alt="Clear search">
            <input
            data-bind="projectSearch: {
                            data: data,
                            onSelected: onSelectedProject
                        },
                        value: selectedProjectName,
                        attr: {disabled: hasSelectedProject()}"
                class="typeahead ob-typeahead-input form-control"
                name="project"
                type="text"
                placeholder="Type to search for a project">
        </div><!-- end .form-group -->

        <!-- Component search typeahead -->
        <!-- ko if: showComponents && hasSelectedProject() -->
        <div data-bind="css: {'has-success': hasSelectedComponent()}" class="form-group">
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
                    value: selectedComponentName,
                    attr: {disabled: hasSelectedComponent()}"
                class="typeahead ob-typeahead-input form-control"
                name="component"
                type="text"
                placeholder="Optional: Type to search for a component">
        </div><!-- end .form-group -->
        <!-- /ko -->
    </div> <!-- end .ob-search -->
    <button type="submit" data-bind="visible: showSubmit(), text: params.submitText || 'Submit'"
            class="btn btn-primary pull-right" >
    </button>
</form>
</template>

## The onboarding "register" widget
<template id="osf-ob-register">
<li class="ob-list-item list-group-item">
    <div data-bind="click: toggle" class="ob-header pointer">
        <h3 class="ob-heading list-group-item-heading">Register a project</h3>
        <i data-bind="css: {'icon-plus': !isOpen(), 'icon-minus': isOpen()}"
            class="pointer ob-expand-icon icon-large pull-right">
        </i>
    </div><!-- end ob-header -->

    <div data-bind="visible: isOpen()">
        <div class="row">
            <div class="col-md-12" >
                <osf-project-search
                params="data: data,
                        onSubmit: onRegisterSubmit,
                        enableComponents: false,
                        submitTest: 'Continue registration...'">
                </osf-project-search>
            </div><!-- end col-md -->
        </div><!-- end row -->
    </div>
</li> <!-- end .ob-list -->
</template>

## TODO: Remove unnecessary IDs
<template id="osf-ob-uploader">
<li class="ob-list-item list-group-item">
    <div class="pointer">
        <h3 class="ob-heading">Upload file(s)</h3>
    </div><!-- end ob-unselectable -->


    <div class="row">
        <div class="col-md-12">
            <h4>1. Drop file (or click below)</h4>

            <!-- Dropzone -->
            <div data-bind="click: clearMessages(), visible: enableUpload()" id="obDropzone" class="ob-dropzone ob-dropzone-box pull-left"></div>

            <!-- File queue display -->
            <div data-bind="visible: !enableUpload()" class="ob-dropzone-selected ob-dropzone-box pull-left">
                <img data-bind="attr: {src: iconSrc()}" class="ob-dropzone-icon" alt="File icon">
                <div data-bind="text: filename" class="ob-dropzone-filename"></div>
                <progress
                    data-bind="attr: {value: progress()}"
                        class="ob-upload-progress" max="100"></progress>
                <img data-bind="click: clearDropzone"
                    class="ob-clear-button pull-right" src="/static/img/close2.png" alt="Clear search">
            </div>

        </div><!-- end col-md -->
    </div><!-- end row -->
    <div class="row">
        <div class="col-md-12">
            <h4> 2. Select a project</h4>
            <osf-project-search
            params="data: data,
                    onSubmit: startUpload,
                    submitTest: 'Upload'">
            </osf-project-search>
        </div>
    </div><!-- end row -->
    <div data-bind="text: message(), attr: {class: messageClass()}" ></div>
</li> <!-- end .ob-list -->
</template>

<template id="project-create-form">
<form id="creationForm" data-bind="submit: submitForm">
    ## Uncomment for debugging
    ## <pre data-bind="text: ko.utils.stringifyJson($data, null, 2)"></pre >
    <div class="row">
        <div class="col-md-12">
            <label for="title">Title</label>
            <input class="form-control" type="text" name="title" data-bind="value: title, valueUpdate:'input'" placeholder="Required">

            <!-- flashed validation message -->
            <span class="text-danger" data-bind="text: errorMessage"></span>
            <br />

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
</template>
