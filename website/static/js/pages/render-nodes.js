'use strict';

var $osf = require('js/osfHelpers');

// model for components, due to simplicity did not create a new file
var ComponentControl = {};

// binds to component scope in render_nodes.mako
$osf.applyBindings(ComponentControl, '#componentScope');
