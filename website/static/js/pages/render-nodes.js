'use strict';

var $osf = require('js/osfHelpers');
var $ = require('jquery');

// model for components, due to simplicity did not create a new file
var ComponentControl = {};

// binds to component scope in render_nodes.mako
$(document).ready(function() {
    $('.componentScope').each(function(i) {
       $(this).attr('id', 'componentScope' + i);
       $osf.applyBindings(ComponentControl, this);
    });
});
