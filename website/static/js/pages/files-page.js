var Rubeus = require('rubeus');
var Comment = require('../comment.js');

// Don't show dropped content if user drags outside grid
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

// Initialize the filebrowser
new Rubeus('#myGrid', {
    data: window.contextVars.node.urls.api + 'files/grid',
    searchInput: '#fileSearch',
    uploads: true
});

// Initialize comment pane w/ it's viewmodel
var $comments = $('.comments');
if ($comments.length) {
    var userName = window.contextVars.currentUser.name;
    var canComment = window.contextVars.currentUser.canComment;
    var hasChildren = window.contextVars.node.hasChildren;
    var page = 'files';
    Comment.init('.commentPane', 'pane', page, userName, canComment, hasChildren);
}
