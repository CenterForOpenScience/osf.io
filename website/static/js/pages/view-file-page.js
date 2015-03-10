var FileRenderer = require('../filerenderer.js');
var FileRevisions = require('../fileRevisions.js');

if (window.contextVars.renderURL !== undefined) {
    FileRenderer.start(window.contextVars.renderURL, '#fileRendered');
}

new FileRevisions(
    '#fileRevisions',
    window.contextVars.node,
    window.contextVars.file,
    window.contextVars.currentUser.canEdit
);

var Comment = require('../comment.js');

// Initialize comment pane w/ it's viewmodel
var $comments = $('.comments');
if ($comments.length) {
    var userName = window.contextVars.currentUser.name;
    var canComment = window.contextVars.currentUser.canComment;
    var hasChildren = window.contextVars.node.hasChildren;
    var id = window.contextVars.file.id;
    var name = window.contextVars.file.name;
    Comment.init('.commentPane', 'files', id, name, 'pane', userName, canComment, hasChildren);
}

// If the provider is wrong:
var $osf = require('osfHelpers');
var providerWithoutComments = ["box", "dataverse", "googledrive"];
if (providerWithoutComments.indexOf(window.contextVars.file.provider) >= 0) {
    if (window.contextVars.currentUser.canComment) {
        $osf.growl("Comments are not supported for this addon.")
    }
}

