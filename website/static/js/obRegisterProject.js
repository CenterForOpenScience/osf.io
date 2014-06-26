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
    console.log();
    var namespace = 'RegisterProject';

    function ObRegisterProject(){
        var typeaheadsearch  = new TypeaheadSearch(namespace);
        // to  do any of this just edit the click functionality editing the name spaced add_linkk
        $('#addLink'+ namespace).click(function() {
            var url = '/'+ $('#addLink' + namespace).prop('linkID') + '/register'; 
            window.location = url;
        });
    }
    return ObRegisterProject;
}));
