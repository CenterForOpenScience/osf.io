
var FolderCreator = require('../folderCreator.js');

var nodeID = window.contextVars.nodeID;
new FolderCreator('#creationForm', '/api/v1/folder/' + nodeID);
