/** Initialization code for the project discussion page. */
var $ = require('jquery');
var CommentModel = require('js/comment');

// Initialize comment pane w/ it's viewmodel
var id = null;

if (window.contextVars.comment) {
    id = window.contextVars.comment.id;
}

var options = {
    nodeId : window.contextVars.node.id,
    nodeApiUrl: window.contextVars.node.urls.api,
    hostPage: window.contextVars.commentTarget,
    hostName: window.contextVars.commentTargetId,
    mode: 'page',
    userName: window.contextVars.currentUser.name,
    canComment: window.contextVars.currentUser.canComment,
    hasChildren: window.contextVars.node.hasChildren,
    thread_id: id
};

CommentModel.init('.discussion', options);