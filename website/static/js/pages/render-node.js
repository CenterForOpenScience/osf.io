'use strict';

var $ = require('jquery');
var m = require('mithril');
var LogFeed = require('js/logFeed.js');

var component = window.contextVars.component;
var canView = window.contextVars.user.canView;

$(document).ready(function() {
    if (canView) {
        var nodeLogFeed = 'logFeed-' + component.id;
        m.mount(document.getElementById(nodeLogFeed), m.component(LogFeed.LogFeed, {node: component, limitLogs: true}));
    }
});
