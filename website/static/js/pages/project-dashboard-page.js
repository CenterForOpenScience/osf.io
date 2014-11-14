/** Initialization code for the project dashboard. */

var $ = require('jquery');
var Rubeus = require('rubeus');

var LogFeed = require('../logFeed.js');
var pointers = require('../pointers.js');

var Comment = require('../comment.js');

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

// Initialize controller for "Add Links" modal
new pointers.PointerManager('#addPointer', window.contextVars.node.title);

// Listen for the nodeLoad event (prevents multiple requests for data)
$('body').on('nodeLoad', function() {
    new LogFeed('#logScope', nodeApiUrl + 'log/');
});


// Initialize comment pane w/ it's viewmodel
var $comments = $('#comments');
if ($comments.length) {
    var userName = window.contextVars.currentUser.name;
    var canComment = window.contextVars.currentUser.canComment;
    var hasChildren = window.contextVars.node.hasChildren;
    Comment.init('#commentPane', userName, canComment, hasChildren);
}
