'use strict';

var $ = require('jquery');
var m = require('mithril');
var LogFeed = require('js/logFeed.js');

var project = window.contextVars.project;
var component = window.contextVars.component;
var canView = window.contextVars.user.canView;

$(document).ready(function() {
    if (canView) {
        var componentLogFeed = 'logFeed-' + component.id;
        m.mount(document.getElementById(componentLogFeed), m.component(LogFeed.LogFeed, {node: component}));
    }
});
