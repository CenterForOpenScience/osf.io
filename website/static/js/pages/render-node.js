'use strict';

var $ = require('jquery');
var m = require('mithril');
var LogFeed = require('js/logFeed.js');

var node = window.contextVars.node;
var canView = window.contextVars.user.canView;

$(document).ready(function() {
    if (canView) {
        var nodeLogFeed = 'logFeed-' + node.id;
        m.mount(document.getElementById(nodeLogFeed), m.component(LogFeed.LogFeed, {node: node, limitLogs: true}));
    }
});
