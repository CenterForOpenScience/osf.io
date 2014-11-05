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
                        attr: {disabled: hasSelectedProject(),
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
                    attr: {disabled: hasSelectedComponent(),
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
                        submitText: 'Continue registration...'">
                </osf-project-search>
            </div><!-- end col-md -->
        </div><!-- end row -->
    </div>
</li> <!-- end .ob-list -->
</template>

<template id="osf-ob-uploader">
<li class="ob-list-item list-group-item">
    <div data-bind="click: toggle" class="ob-header pointer">
        <h3 class="ob-heading list-group-item-heading">Upload file(s)</h3>
        <i data-bind="css: {'icon-plus': !isOpen(), 'icon-minus': isOpen()}"
            class="pointer ob-expand-icon icon-large pull-right">
        </i>
    </div><!-- end ob-header -->


    <div data-bind="visible: isOpen()">
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
</li> <!-- end .ob-list -->
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

            <label>Description (Optional)</label>
            <textarea data-bind="value: description"class="form-control" name="description"
                ></textarea>
            <br />
            <label>Template (Optional)</label>
            <span class="help-block">Start typing to search. Selecting project as template will duplicate its structure in the new project without importing the content of that project.</span>
            <input type="hidden" id="templates" class="select2-container" style="width: 100%">
        </div>
    </div>
    <br />
    <div class="row">
        <div class="col-md-12">
            <button class="btn btn-primary pull-right" type="submit">Create</button>
        </div>
    </div>
</form>
</template>

<template id="osf-ob-goto">
<li class="ob-list-item list-group-item">
    <div data-bind="click: toggle" class="ob-header pointer">
        <h3 class="ob-heading list-group-item-heading">Go to my project</h3>
        <i data-bind="css: {'icon-plus': !isOpen(), 'icon-minus': isOpen()}"
            class="pointer ob-expand-icon icon-large pull-right">
        </i>
    </div><!-- end ob-header -->
    <div class="row">
        <div data-bind="visible: isOpen()">
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
</li> <!-- end .ob-list -->
</template>
