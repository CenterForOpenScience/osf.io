## A reuseable OSF project typeahead search widget. Uses the custom projectSearch binding handler.
<template id="osf-project-search">
<form data-bind="submit: onSubmit">
    <div class="ob-search">
        ## Add label for proper spacing
        <div data-bind="css: {'has-success': hasSelected()}" class="form-group">
            <label for="project"></label>
            ## TODO: Fix placement of clear search button
            <img
                data-bind="click: clearSearch, visible: hasSelected()"
                class="ob-clear-button" src="/static/img/close2.png">
        <input
            data-bind="projectSearch: {onSelected: onSelected}, attr: {disabled: hasSelected()}"
            class="typeahead ob-typeahead-input form-control"
            name="project"
            type="text"
            placeholder="Type to search for a project">
        </div>
    </div> <!-- end .ob-search -->
    <button type="submit" data-bind="visible: hasSelected(), text: params.submitText || 'Submit'"
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
    </div><!-- end ob-reveal -->
</li> <!-- end .ob-list -->
</template>
