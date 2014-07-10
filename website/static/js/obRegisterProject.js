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
    var namespace = 'RegisterProject';

    function ObRegisterProject(){
        var $addLink = $('#addLink' + namespace);
        var typeaheadsearch3  = new TypeaheadSearch(namespace, 'Project', 0);
        // to  do any of this just edit the click functionality editing the name spaced add_linkk
        $addLink.click(function() {
            var url = '/'+ $addLink.prop('linkIDProject') + '/register'; 
            window.location = url;
        });
    }
    return ObRegisterProject;
}));
