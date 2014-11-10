/** Initialization code for the project dashboard. */

var $ = require('jquery');
var Rubeus = require('rubeus');

var LogFeed = require('../logFeed.js');
var NodeControl = require('../nodeControl.js');

var nodeApiUrl = window.contextVars.node.urls.api;

// Initialize the filebrowser
new Rubeus('#myGrid', {
    data: nodeApiUrl + 'files/grid/',
    columns: [Rubeus.Col.Name],
    uploads: false,
    width: '100%',
    height: 600,
    progBar: '#filetreeProgressBar',
    searchInput: '#fileSearch'
});

$(function() {
    // Get project data from the server and initiate KO modules
    $.getJSON(nodeApiUrl, function(data) {
        // Initialize nodeControl and logFeed on success
        new NodeControl('#projectScope', data);
        $('body').trigger('nodeLoad', data);
    });
});

// Listen for the nodeLoad event (prevents multiple requests for data)
$('body').on('nodeLoad', function() {
    new LogFeed('#logScope', nodeApiUrl + 'log/');
});
