var RevisionTable = require('./storageRevisions.js');

new RevisionTable(
            '#revisionScope',
            window.contextVars.node.title,
            window.contextVars.filePath,
            window.contextVars.currentUser.canEdit,
            {
                files: window.contextVars.node.files,
                download: window.contextVars.node.download,
                delete: window.contextVars.node.delete,
                revisions: window.contextVars.node.revisions
            }
        );
