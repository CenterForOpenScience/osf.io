'use strict';

var $osf = require('js/osfHelpers');
var $ = require('jquery');
var m = require('mithril');
var LogFeed = require('js/components/logFeed.js');

// model for components, due to simplicity did not create a new file
var ComponentControl = {};

// binds to component scope in render_nodes.mako
$('.render-nodes-list').each(function() {
    $osf.applyBindings(ComponentControl, this);
});

var nodes = window.contextVars.nodes;
$(document).ready(function() {
    for (var i = 0; i < nodes.length; ++i) {
        var node = nodes[i].node;
        node.id = nodes[i].id;
        if (node.can_view && !node.archiving && !node.is_retracted) {
            var nodeLogFeed = 'logFeed-' + node.id;
            m.mount(document.getElementById(nodeLogFeed), m.component(LogFeed.LogFeed, {node: node, limitLogs: true}));
        }
    }
});
