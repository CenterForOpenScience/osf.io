/** Initialization code for the project discussion page. */
var $ = require('jquery');
var Comment = require('../comment.js');

// Initialize comment pane w/ it's viewmodel
var userName = window.contextVars.currentUser.name;
var canComment = window.contextVars.currentUser.canComment;
var hasChildren = window.contextVars.node.hasChildren;
var target = window.contextVars.commentTarget;
target = (target==='None')? 'node' : target;
var targetId = window.contextVars.commentTargetId;
var id = null;
if (window.contextVars.comment) {
    id = window.contextVars.comment.id;
}
Comment.init('.discussion', target, targetId, 'page', userName, canComment, hasChildren, id);