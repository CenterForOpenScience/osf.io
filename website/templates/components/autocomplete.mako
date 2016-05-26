<template id="osf-search">
    <form data-bind="submit: onSubmit">
        <!-- Project search typeahead -->
        <div data-bind="css: {'has-success': hasItemSelected()}" class="form-group ob-input">
            <img
                data-bind="click: onClear, visible: hasItemSelected()"
                class="ob-clear-button pull-right" src="/static/img/close2.png" alt="Clear search">
            <input class="osf-typeahead typeahead form-control"
                    data-bind="attr:{ 
                               readonly: hasItemSelected(),
                               placeholder: placeholder || ''
                               }"/>
        </div><!-- end .form-group -->
        <button type="submit" data-bind="visible: hasItemSelected(), html: submitText()" class="btn btn-primary pull-right"> </button>
</form>
</template>
