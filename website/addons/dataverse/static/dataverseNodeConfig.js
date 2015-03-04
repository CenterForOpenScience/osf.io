/**
* Module that controls the {{cookiecutter.full_name}} node settings. Includes Knockout view-model
* for syncing data.
*/

var ko = require('knockout');
var bootbox = require('bootbox');
require('knockout-punches');
var osfHelpers = require('osfHelpers');
var language = require('osfLanguage').Addons.dataverse;

ko.punches.enableAll();

function ViewModel(url) {
    var self = this;
    self.url = url;
    self.urls = ko.observable();
    self.apiToken = ko.observable();

    self.ownerName = ko.observable();
    self.nodeHasAuth = ko.observable(false);
    self.userHasAuth = ko.observable(false);
    self.userIsOwner = ko.observable(false);
    self.connected = ko.observable(false);
    self.loadedSettings = ko.observable(false);
    self.loadedDatasets = ko.observable(false);
    self.submitting = ko.observable(false);

    self.dataverses = ko.observableArray([]);
    self.datasets = ko.observableArray([]);
    self.badDatasets = ko.observableArray([]);

    self.savedDatasetDoi = ko.observable();
    self.savedDatasetTitle = ko.observable();
    self.savedDataverseAlias = ko.observable();
    self.savedDataverseTitle = ko.observable();
    self.datasetWasFound = ko.observable(false);

    self.savedDatasetUrl = ko.computed(function() {
        return (self.urls()) ? self.urls().datasetPrefix + self.savedDatasetDoi() : null;
    });
    self.savedDataverseUrl = ko.computed(function() {
        return (self.urls()) ? self.urls().dataversePrefix + self.savedDataverseAlias() : null;
    });

    self.selectedDataverseAlias = ko.observable();
    self.selectedDatasetDoi = ko.observable();
    self.selectedDataverseTitle = ko.computed(function() {
        for (var i=0; i < self.dataverses().length; i++) {
            var data = self.dataverses()[i];
            if (data.alias === self.selectedDataverseAlias()) {
                return data.title;
            }
        }
        return null;
    });
    self.selectedDatasetTitle = ko.computed(function() {
        for (var i=0; i < self.datasets().length; i++) {
            var data = self.datasets()[i];
            if (data.doi === self.selectedDatasetDoi()) {
                return data.title;
            }
        }
        return null;
    });
    self.dataverseHasDatasets = ko.computed(function() {
        return self.datasets().length > 0;
    });

    self.showDatasetSelect = ko.computed(function() {
        return self.loadedDatasets() && self.dataverseHasDatasets();
    });
    self.showNoDatasets = ko.computed(function() {
        return self.loadedDatasets() && !self.dataverseHasDatasets();
    });
    self.showLinkedDataset = ko.computed(function() {
        return self.savedDatasetDoi();
    });
    self.showLinkDataverse = ko.computed(function() {
        return self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
    });
    self.credentialsChanged = ko.computed(function() {
        return self.nodeHasAuth() && !self.connected();
    });
    self.showInputCredentials = ko.computed(function() {
        return  (self.credentialsChanged() && self.userIsOwner()) ||
            (!self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings());
    });
    self.hasDataverses = ko.computed(function() {
        return self.dataverses().length > 0;
    });
    self.hasBadDatasets = ko.computed(function() {
        return self.badDatasets().length > 0;
    });
    self.showNotFound = ko.computed(function() {
        return self.savedDatasetDoi() && self.loadedDatasets() && !self.datasetWasFound();
    });
    self.showSubmitDataset = ko.computed(function() {
        return self.nodeHasAuth() && self.connected() && self.userIsOwner();
    });
    self.enableSubmitDataset = ko.computed(function() {
        return !self.submitting() && self.dataverseHasDatasets() &&
            self.savedDatasetDoi() !== self.selectedDatasetDoi();
    });

    /**
        * Update the view model from data returned from the server.
        */

    self.updateFromData = function(data) {
        self.urls(data.urls);
        self.apiToken(data.apiToken);
        self.ownerName(data.ownerName);
        self.nodeHasAuth(data.nodeHasAuth);
        self.userHasAuth(data.userHasAuth);
        self.userIsOwner(data.userIsOwner);

        if (self.nodeHasAuth()){
            self.dataverses(data.dataverses);
            self.savedDataverseAlias(data.savedDataverse.alias);
            self.savedDataverseTitle(data.savedDataverse.title);
            self.selectedDataverseAlias(data.savedDataverse.alias);
            self.savedDatasetDoi(data.savedDataset.doi);
            self.savedDatasetTitle(data.savedDataset.title);
            self.connected(data.connected);
            if (self.userIsOwner()) {
                self.getDatasets(); // Sets datasets, selectedDatasetDoi
            }
        }
    };

    // Update above observables with data from the server
    $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        // Update view model
        self.updateFromData(response.result);
        self.loadedSettings(true);
    }).fail(function(xhr, textStatus, error) {
        self.changeMessage(language.userSettingsError, 'text-warning');
        Raven.captureMessage('Could not GET dataverse settings', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    self.setInfo = function() {
        self.submitting(true);
        osfHelpers.postJSON(
            self.urls().set,
            ko.toJS({
                dataverse: {alias: self.selectedDataverseAlias},
                dataset: {doi: self.selectedDatasetDoi}
            })
        ).done(function() {
            self.submitting(false);
            self.savedDataverseAlias(self.selectedDataverseAlias());
            self.savedDataverseTitle(self.selectedDataverseTitle());
            self.savedDatasetDoi(self.selectedDatasetDoi());
            self.savedDatasetTitle(self.selectedDatasetTitle());
            self.datasetWasFound(true);
            self.changeMessage('Settings updated.', 'text-success', 5000);
        }).fail(function(xhr, textStatus, error) {
            self.submitting(false);
            var errorMessage = (xhr.status === 410) ? language.datasetDeaccessioned :
                (xhr.status = 406) ? language.forbiddenCharacters : language.setDatasetError;
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with Dataverse', {
                url: self.urls().set,
                textStatus: textStatus,
                error: error
            });
        });
    };

    /**
        * Looks for dataset in list of datasets when first loaded.
        * This prevents an additional request to the server, but requires additional logic.
        */
    self.findDataset = function() {
        for (var i in self.datasets()) {
            if (self.datasets()[i].doi === self.savedDatasetDoi()) {
                self.datasetWasFound(true);
                return;
            }
        }
    };

    self.getDatasets = function() {
        self.datasets([]);
        self.badDatasets([]);
        self.loadedDatasets(false);
        return osfHelpers.postJSON(
            self.urls().getDatasets,
            ko.toJS({alias: self.selectedDataverseAlias})
        ).done(function(response) {
            self.datasets(response.datasets);
            self.badDatasets(response.badDatasets);
            self.loadedDatasets(true);
            self.selectedDatasetDoi(self.savedDatasetDoi());
            self.findDataset();
        }).fail(function() {
            self.changeMessage('Could not load datasets', 'text-danger');
        });
    };

    /** Send POST request to authorize Dataverse */
    self.sendAuth = function() {
        return osfHelpers.postJSON(
            self.urls().create,
            ko.toJS({api_token: self.apiToken})
        ).done(function() {
            // User now has auth
            authorizeNode();
        }).fail(function(xhr) {
            var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
        });
    };

    /**
    *  Send PUT request to import access token from user profile.
    */
    self.importAuth = function() {
        bootbox.confirm({
            title: 'Link to Dataverse Account?',
            message: 'Are you sure you want to authorize this project with your Dataverse credentials?',
            callback: function(confirmed) {
                if (confirmed) {
                    authorizeNode();
                }
            }
        });
    };

    self.clickDeauth = function() {
        bootbox.confirm({
            title: 'Deauthorize?',
            message: language.confirmNodeDeauth,
            callback: function(confirmed) {
                if (confirmed) {
                    sendDeauth();
                }
            }
        });
    };

    function authorizeNode() {
        return osfHelpers.putJSON(
            self.urls().importAuth,
            {}
        ).done(function(response) {
            self.updateFromData(response.result);
            self.changeMessage(language.authSuccess, 'text-success', 3000);
        }).fail(function() {
            self.changeMessage(language.authError, 'text-danger');
        });
    }

    function sendDeauth() {
        return $.ajax({
            url: self.urls().deauthorize,
            type: 'DELETE'
        }).done(function() {
            self.nodeHasAuth(false);
            self.userIsOwner(false);
            self.connected(false);
            self.changeMessage(language.deauthSuccess, 'text-success', 5000);
        }).fail(function() {
            self.changeMessage(language.deauthError, 'text-danger');
        });
    }

    /** Change the flashed status message */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    };

}

function DataverseNodeConfig(selector, url) {
    // Initialization code
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    osfHelpers.applyBindings(self.viewModel, '#dataverseScope');
}
module.exports = DataverseNodeConfig;
