var DataverseFileTable = require('./dataverseViewFile.js');

var url = window.contextVars.node.urls.info;
new DataverseFileTable('#dataverseScope', url);


var nodeApiUrl = window.contextVars.node.urls.api;
var FileRenderer = require('js/filerenderer.js');

$(document).ready(function() {
    if (window.contextVars.renderURL !== undefined) {
        FileRenderer.start(window.contextVars.renderURL, '#fileRendered');
    }
});