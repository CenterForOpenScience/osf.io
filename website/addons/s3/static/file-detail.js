var DeleteFile = require('../../../static/js/deleteFile.js');

new DeleteFile('#s3Scope', window.contextVars.node.urls);

var Comment = require('../../../static/js/comment.js');

// Initialize comment pane w/ it's viewmodel
var $comments = $('.comments');
if ($comments.length) {
    var userName = window.contextVars.currentUser.name;
    var canComment = window.contextVars.currentUser.canComment;
    var hasChildren = window.contextVars.node.hasChildren;
    var id = window.contextVars.file_id;
    var name = window.contextVars.file_name;
    Comment.init('.commentPane', 'files', id, name, 'pane', userName, canComment, hasChildren);
}