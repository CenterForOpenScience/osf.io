;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['typeahead', 'typeaheadSearch'], function() {
            global.ObRegisterProject = factory(jQuery);
            $script.done('obRegisterProject');
        });
    } else {
        global.ObRegisterProject = factory(jQuery);
    }
}(this, function ($) {
    'use strict';

    var namespace = 'register-project';

    function ObRegisterProject(){

        var typeaheadsearch  = new TypeaheadSearch(namespace);
        // to  do any of this just edit the click functionality editing the name spaced add_linkk
        $('#add-link-'+ namespace).click(function() {
            var url = '/'+ $('#add-link-' + namespace).prop('linkID') + '/register'; 
            window.location = url;
        });
    }
    return ObRegisterProject;
}));
