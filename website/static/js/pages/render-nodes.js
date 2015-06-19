'use strict';

var $osf = require('js/osfHelpers');
var $ = require('jquery');
var ko = require('knockout');

// model for components, due to simplicity did not create a new file
var ComponentControl = {
     anonymousUserName:ko.observable('<em>A user</em>')
};

// binds to component scope in render_nodes.mako
$('.render-nodes-list').each(function() {
    $osf.applyBindings(ComponentControl, this);
});

