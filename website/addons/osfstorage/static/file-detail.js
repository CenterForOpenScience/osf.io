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
