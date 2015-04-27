var FileRenderer = require('../filerenderer.js');
var FileRevisions = require('../fileRevisions.js');

if (window.contextVars.renderURL !== undefined) {
    FileRenderer.start(window.contextVars.renderURL, '#fileRendered');
}

$(document).ready(function() {
    new FileRevisions(
        '#fileRevisions',
        window.contextVars.node,
        window.contextVars.file,
        window.contextVars.currentUser.canEdit
    );
});

var Comment = require('js/comment');

// Initialize comment pane w/ it's viewmodel
var $comments = $('.comments');
if ($comments.length) {
    var options = {
        hostPage: 'files',
        hostName: window.contextVars.file.id,
        mode: 'pane',
        userName: window.contextVars.currentUser.name,
        canComment: window.contextVars.currentUser.canComment,
        hasChildren: window.contextVars.node.hasChildren
    };
    Comment.init('.comment-pane', options);
}

