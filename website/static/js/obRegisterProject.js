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

    function redirect_to_poc(poc){
        window.location = '/'+ $('#addLink' + namespace).prop('linkID' + poc) + '/register';
    }

    function ObRegisterProject(){
        var $addLink = $('#addLink' + namespace);
        var typeaheadsearch3  = new TypeaheadSearch(namespace, 'Project', 1);
        var typeaheadsearch4  = new TypeaheadSearch(namespace, 'Component', 0);

        // to  do any of this just edit the click functionality editing the name spaced add_link
        $addLink.click(function() {
            if(typeof $addLink.prop('linkIDComponent')!=='undefined'){
                redirect_to_poc('Component');
            }else{
                redirect_to_poc('Project');
            }
        });
    }

    return ObRegisterProject;
}));
