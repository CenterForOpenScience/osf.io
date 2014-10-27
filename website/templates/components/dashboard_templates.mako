## A reuseable OSF project typeahead search widget. Uses the custom projectSearch binding handler.
<template id="osf-project-search">
<form data-bind="submit: onSubmit">
    <div class="ob-search">
        ## Add label for proper spacing
        <div data-bind="css: {'has-success': hasSelected()}" class="form-group">
            <label for="project"></label>
            <img
                data-bind="click: clearSearch, visible: hasSelected()"
                class="ob-clear-button" src="/static/img/close2.png">
        <input
        data-bind="projectSearch: {onSelected: onSelected},
                    value: selectedProjectName,
                    attr: {disabled: hasSelected()}"
            class="typeahead ob-typeahead-input form-control"
            name="project"
            type="text"
            placeholder="Type to search for a project">
        </div>
    </div> <!-- end .ob-search -->
    <button type="submit" data-bind="visible: showSubmit(), text: params.submitText || 'Submit'"
            class="btn btn-primary pull-right" >
    </button>
</form>
</template>

## The onboarding "register" widget
<template id="osf-ob-register">
<li class="ob-list list-group-item">
    <div data-bind="click: toggle" class="pointer">
        <h3 class="ob-heading">Register a project</h3>
        <i data-bind="css: {'icon-plus': !isOpen(), 'icon-minus': isOpen()}"
            class="pointer icon-large pull-right">
        </i>
    </div><!-- end ob-unselectable -->

    <div data-bind="visible: isOpen()">
        <div class="row">
            <div class="col-md-12" >
                <div data-bind="component:
                    {
                        name: 'osf-project-search',
                        params: {onSubmit: onRegisterSubmit, submitText: 'Continue registration...'}
                    }">
                </div>
            </div><!-- end col-md -->
        </div><!-- end row -->
    </div>
</li> <!-- end .ob-list -->
</template>

## TODO: Remove unnecessary IDs
<template id="osf-ob-uploader">
<li class="ob-list list-group-item">
    <div class="pointer">
        <h3 class="ob-heading">Upload file(s)</h3>
    </div><!-- end ob-unselectable -->

    <div class="row">
        <div class="col-md-12">
            <h4>1. Drop file (or click below)</h4>

            <!-- Dropzone -->
            <div data-bind="visible: enableUpload()" id="obDropzone" class="ob-dropzone-box pull-left"></div>

            <!-- File queue display -->
            <div data-bind="visible: !enableUpload()" id="obDropzoneSelected" class="ob-dropzone-box pull-left">
                <img data-bind="attr: {src: iconSrc()}" id="uploadIcon">
                <div data-bind="text: filename" id="obDropzoneFilename"></div>
                <progress
                data-bind="attr: {value: progress()}"
                    class="ob-reveal" id="uploadProgress" max="100"></progress>
                <img data-bind="click: clearDropzone"
                    class="ob-clear-button" id="clearDropzone" src="/static/img/close2.png">
            </div>

        </div><!-- end col-md -->
    </div><!-- end row -->
    <div class="row">
        <div class="col-md-12">
            <h4> 2. Select a project</h4>
            <div data-bind="component:
                {
                    name: 'osf-project-search',
                    params: {
                        onSubmit: startUpload,
                        submitText: 'Upload',
                    }
                }">
            </div>
        </div>
    </div><!-- end row -->
    <div data-bind="text: message(), attr: {class: messageClass()}" ></div>
</li> <!-- end .ob-list -->
</template>
