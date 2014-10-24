;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['typeaheadSearch'], function() {
            global.ObRegisterProject = factory(jQuery);
            $script.done('obRegisterProject');
        });
    } else {
        global.ObRegisterProject = factory(jQuery);
    }
}(this, function ($) {
    'use strict';
    var namespace = 'RegisterProject';

    function redirectToPOC(poc){
        window.location = '/'+ $('#addLink' + namespace).prop('linkID' + poc) + '/register/';
    }

    function ObRegisterProject(){
        var $addLink = $('#addLink' + namespace);
        self.projectTypeahead  = new TypeaheadSearch(namespace, 'Project', true);
        self.componentTypeahead  = new TypeaheadSearch(namespace, 'Component', false);

        // to  do any of this just edit the click functionality editing the name spaced add_link
        $addLink.click(function() {
            if(typeof $addLink.prop('linkIDComponent')!=='undefined'){
                redirectToPOC('Component');
            }else{
                redirectToPOC('Project');
            }
        });
    }

    return ObRegisterProject;
}));
