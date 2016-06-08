'use strict';

var $osf = require('js/osfHelpers');
var $ = require('jquery');
var m = require('mithril');
var LogFeed = require('js/logFeed.js');

// model for components, due to simplicity did not create a new file
var ComponentControl = {};

var project = window.contextVars.project;
var components = window.contextVars.components;

// binds to component scope in render_nodes.mako
$('.render-nodes-list').each(function() {
    $osf.applyBindings(ComponentControl, this);
});

$(document).ready(function() {
    m.mount(document.getElementById('logFeed'), m.component(LogFeed.LogFeed, {node: project}));
    for (var i = 0; i < components.length; ++i) {
        var component = components[i];
        var componentLogFeed = 'logFeed-' + component.id;
        m.mount(document.getElementById(componentLogFeed), m.component(LogFeed.LogFeed, {node: component}));
    }
});
