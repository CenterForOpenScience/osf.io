'use strict';

var $osf = require('js/osfHelpers');
var $ = require('jquery');

//ComponentActions namespace needed for deleting components.
var ComponentActions = require('js/componentActions');

// binds to component scope in render_nodes.mako
$('.render-nodes-list').each(function() {
    $osf.applyBindings(ComponentActions, this);
});
