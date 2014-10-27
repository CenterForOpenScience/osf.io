<template id="osf-project-search">
<form data-bind="submit: onSubmit">
    <div class="ob-search">
        ## TODO: Clear search button
        ## <img data-bind="click: clearSearch" class="ob-clear-button" src="/static/img/close2.png">
        ## Add label for proper spacing
        <div class="form-group">
            <label for="project"></label>
        <input
        data-bind="projectSearch: {onSelected: onSelected}"
            class="typeahead form-control"
            name="project"
            type="text"
            placeholder="Type to search for a project or component">
        </div>
    </div> <!-- end .ob-search -->
    ## TODO: don't hardcode button text
    <button type="submit" data-bind="visible: hasSelected(), text: params.submitText || 'Submit'"
            class="btn btn-primary pull-right" >
    </button>
</form>
</template>

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
    </div><!-- end ob-reveal -->
</li> <!-- end .ob-list -->
</template>
