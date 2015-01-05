var $ = require('jquery');
var Comment = require('../comment.js');
var Raven = require('raven-js');

var $comments = $('.comments');
if ($comments.length) {
    var userName = window.contextVars.currentUser.name;
    var canComment = window.contextVars.currentUser.canComment;
    var hasChildren = window.contextVars.node.hasChildren;
    var title = window.contextVars.wikiName;
    Comment.init('.commentPane', 'wiki', title, 'pane', userName, canComment, hasChildren);
}