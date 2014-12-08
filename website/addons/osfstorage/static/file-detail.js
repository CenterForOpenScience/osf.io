var RevisionTable = require('./storageRevisions.js');

new RevisionTable(
            '#revisionScope',
            window.contextVars.node.title,
            window.contextVars.filePath,
            window.contextVars.currentUser.canEdit,
            {
                files: window.contextVars.node.urls.files,
                download: window.contextVars.node.urls.download,
                delete: window.contextVars.node.urls.delete,
                revisions: window.contextVars.node.urls.revisions
            }
        );
