var RevisionTable = require('./storageRevisions.js');

new RevisionTable(
    '#revisionScope',
    window.contextVars.node.title,
    window.contextVars.filePath,
    window.contextVars.currentUser.canEdit,
    {
        files: window.contextVars.node.urls.files,
        download: window.contextVars.node.urls.download,
        revisions: window.contextVars.node.urls.revisions
    }
);

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