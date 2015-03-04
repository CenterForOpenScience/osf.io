var RevisionTable = require('./revisions.js');

var url = window.contextVars.node.urls.revisions_url;
new RevisionTable('#revisionScope', url);
