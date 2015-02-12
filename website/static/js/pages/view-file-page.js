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

// TODO: Workaround for highlighting the Files tab in the project navbar. Rethink.
$(document).ready(function(){
    $('.osf-project-navbar li:contains("Files")').addClass('active');
});
