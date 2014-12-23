/** Initialization code for the project discussion page. */
var $ = require('jquery');
var Comment = require('../comment.js');

// Initialize comment pane w/ it's viewmodel
var userName = window.contextVars.currentUser.name;
var canComment = window.contextVars.currentUser.canComment;
var hasChildren = window.contextVars.node.hasChildren;
Comment.init('#discussion-overview', 'overview', userName, canComment, hasChildren);
Comment.init('#discussion-files', 'files', userName, canComment, hasChildren);

$(".discussion-btn").each(function() {
    $(this).click(function(){
        $(".discussion").hide();
        var discussion_id = $(this).attr('id');
        var len = discussion_id.length;
        discussion_id = '#' + discussion_id.substring(0, len - 4);
        $(discussion_id).show();
    });
});