'use strict';

var $osf = require('js/osfHelpers');
var $ = require('jquery');
var ko = require('knockout');

// model for components, due to simplicity did not create a new file
var ComponentControl = {};

// binds to component scope in render_nodes.mako
$('.render-nodes-list').each(function(i) {
    var isBound = !!ko.dataFor(this);
    $(this).attr('id', 'renderNodesList' + i);
    if(!isBound) {
        $osf.applyBindings(ComponentControl, this);
    }
});

