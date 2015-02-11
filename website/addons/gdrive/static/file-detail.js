var RevisionTable = require('./revisions_gdrive.js');

var url = window.contextVars.node.urls.revisions_url;
new RevisionTable('#revisionScope', url);
