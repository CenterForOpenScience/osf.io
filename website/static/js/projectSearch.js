;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['typeaheadSearch'], function() {
            global.ProjectSearch = factory(jQuery);
            $script.done('projectSearch');
        });
    } else {
        global.ProjectSearch = factory(jQuery);
    }
}(this, function ($) {
    'use strict';

    var namespace = 'register_project';

    function ProjectSearch(){
        TypeaheadSearch(namespace);
        // to  do any of this just edit the click functionality editing the name spaced add_linkk
        $('#add_link_'+ namespace).click(function() {
            var url = '/'+ $('#add_link_' + namespace).prop('linkID') + '/register/';
            window.location = url;
        });
    }

    return ProjectSearch;
}));
