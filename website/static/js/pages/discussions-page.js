/** Initialization code for the project discussion page. */
var $ = require('jquery');
var Comment = require('../comment.js');

// Initialize comment pane w/ it's viewmodel
var userName = window.contextVars.currentUser.name;
var canComment = window.contextVars.currentUser.canComment;
var hasChildren = window.contextVars.node.hasChildren;
var id = null;
if (window.contextVars.comment) {
    id = window.contextVars.comment.id;
}
Comment.init('.discussion', 'page', userName, canComment, hasChildren, id);