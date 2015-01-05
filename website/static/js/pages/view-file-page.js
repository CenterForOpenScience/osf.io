var FileRenderer = require('../filerenderer.js');
FileRenderer.start(window.contextVars.renderURL, '#fileRendered');

// Initialize comment pane w/ it's viewmodel
var $comments = $('.comments');
if ($comments.length) {
    var userName = window.contextVars.currentUser.name;
    var canComment = window.contextVars.currentUser.canComment;
    var hasChildren = window.contextVars.node.hasChildren;
    var page = 'files';
    Comment.init('.commentPane', 'pane', page, userName, canComment, hasChildren);
}