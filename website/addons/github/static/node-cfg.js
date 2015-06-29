'use strict';
var $ = require('jquery');
var bootbox = require('bootbox');

var FlatNodeConfig = require('js/flatNodeConfig').FlatNodeConfig;

var url = window.contextVars.node.urls.api + 'github/settings/';
new FlatNodeConfig('GitHub', '#githubScope', url, 'repo', {
    formatFolders: function(response) {

        var repos = [];
        for(var i = 0; i < response.repo_names.length; i++){
            repos.push(response.user_names[i] + " / " + response.repo_names[i]);
        }
        return repos
    },
    formatFolderName: function(folderName) {
        var newName = folderName.replace(/[^a-zA-Z0-9\-\_]+/g, '-');
        return newName
    },
    fixBadName: function(newName, folderName, self) {
        bootbox.dialog({
            title: 'Repo name will be converted',
            message: 'That name will be converted to <i>' + newName + '</i>. You can try another ' +
            'name, or accept <i>' + newName + '</i> as your repo name.',
            buttons: {
                accept: {
                    label: "Try Different Name",
                    callback: function() {
                        self.openCreateFolder();
                    }
                },
                newName: {
                    label: "Keep Name",
                    callback: function() {
                        self.createFolder(folderName);
                    }
                }
            }
        });
    },
    findFolder: function(settings) {
        return ((settings.repo === null) ? 'None' : settings.user + " / " + settings.repo);
    },
    dataGetSettings: function(data) {
        return data.result;
    }
});
