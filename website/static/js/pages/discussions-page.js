/** Initialization code for the project discussion page. */

var Comment = require('../comment.js');

// Initialize comment pane w/ it's viewmodel
var userName = window.contextVars.currentUser.name;
var canComment = window.contextVars.currentUser.canComment;
var hasChildren = window.contextVars.node.hasChildren;
Comment.init('#discussion-overview', 'overview', userName, canComment, hasChildren);
Comment.init('#discussion-files', 'files', userName, canComment, hasChildren);

