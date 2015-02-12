var FileRenderer = require('../filerenderer.js');
FileRenderer.start(window.contextVars.renderURL, '#fileRendered');

// TODO: Workaround for highlighting the Files tab in the project navbar. Rethink.
$(document).ready(function(){
    $('.osf-project-navbar li:contains("Files")').addClass('active');
});
