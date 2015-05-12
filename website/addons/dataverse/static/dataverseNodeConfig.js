/**
 * Module that controls the Dataverse node settings. Includes Knockout view-model
 * for syncing data.
 */

var ko = require('knockout');
var bootbox = require('bootbox');
require('knockout.punches');
var Raven = require('raven-js');

var osfHelpers = require('js/osfHelpers');

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

    self.savedDatasetDoi = ko.observable();
    self.savedDatasetTitle = ko.observable();
    self.savedDataverseAlias = ko.observable();
    self.savedDataverseTitle = ko.observable();
    self.datasetWasFound = ko.observable(false);

    self.messages = {
        userSettingsError: ko.pureComputed(function() {
            return 'Could not retrieve settings. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        confirmNodeDeauth: ko.pureComputed(function() {
            return 'Are you sure you want to unlink this Dataverse account? This will ' +
                'revoke the ability to view, download, modify, and upload files ' +
                'to datasets on the Dataverse from the OSF. This will not remove your ' +
                'Dataverse authorization from your <a href="' + self.urls().settings + '">user settings</a> ' +
                'page.';
        }),
        confirmImportAuth: ko.pureComputed(function() {
            return 'Are you sure you want to authorize this project with your Dataverse credentials?';
        }),
        deauthError: ko.pureComputed(function() {
            return 'Could not unlink Dataverse at this time. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        deauthSuccess: ko.pureComputed(function() {
            return 'Successfully unlinked your Dataverse account.';
        }),
        authInvalid: ko.pureComputed(function() {
            return 'Your Dataverse API token is invalid.';
        }),
        authError: ko.pureComputed(function() {
            return 'There was a problem connecting to the Dataverse. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        importAuthSuccess: ko.pureComputed(function() {
            return 'Successfully linked your Dataverse account';
        }),
        importAuthError: ko.pureComputed(function() {
            return 'There was a problem connecting to the Dataverse. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        datasetDeaccessioned: ko.pureComputed(function() {
            return 'This dataset has already been deaccessioned on the Dataverse ' +
                'and cannot be connected to the OSF.';
        }),
        forbiddenCharacters: ko.pureComputed(function() {
            return 'This dataset cannot be connected due to forbidden characters ' +
                'in one or more of the dataset\'s file names. This issue has been forwarded to our ' +
                'development team.';
        }),
        setInfoSuccess: ko.pureComputed(function() {
            var filesUrl = window.contextVars.node.urls.web + 'files/';
            return 'Successfully linked dataset \'' + self.savedDatasetTitle() + '\'. Go to the <a href="' +
                filesUrl + '">Files page</a> to view your content.';
        }),
        setDatasetError: ko.pureComputed(function() {
            return 'Could not connect to this dataset. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        getDatasetsError: ko.pureComputed(function() {
            return 'Could not load datasets. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        })
    };

    self.savedDatasetUrl = ko.pureComputed(function() {
        return (self.urls()) ? self.urls().datasetPrefix + self.savedDatasetDoi() : null;
    });
    self.savedDataverseUrl = ko.pureComputed(function() {
        return (self.urls()) ? self.urls().dataversePrefix + self.savedDataverseAlias() : null;
    });

    self.selectedDataverseAlias = ko.observable();
    self.selectedDatasetDoi = ko.observable();
    self.selectedDataverseTitle = ko.pureComputed(function() {
        for (var i = 0; i < self.dataverses().length; i++) {
            var data = self.dataverses()[i];
            if (data.alias === self.selectedDataverseAlias()) {
                return data.title;
            }
        }
        return null;
    });
    self.selectedDatasetTitle = ko.pureComputed(function() {
        for (var i = 0; i < self.datasets().length; i++) {
            var data = self.datasets()[i];
            if (data.doi === self.selectedDatasetDoi()) {
                return data.title;
            }
        }
        return null;
    });
    self.dataverseHasDatasets = ko.pureComputed(function() {
        return self.datasets().length > 0;
    });

    self.showDatasetSelect = ko.pureComputed(function() {
        return self.loadedDatasets() && self.dataverseHasDatasets();
    });
    self.showNoDatasets = ko.pureComputed(function() {
        return self.loadedDatasets() && !self.dataverseHasDatasets();
    });
    self.showLinkedDataset = ko.pureComputed(function() {
        return self.savedDatasetDoi();
    });
    self.showLinkDataverse = ko.pureComputed(function() {
        return self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
    });
    self.credentialsChanged = ko.pureComputed(function() {
        return self.nodeHasAuth() && !self.connected();
    });
    self.showInputCredentials = ko.pureComputed(function() {
        return (self.credentialsChanged() && self.userIsOwner()) ||
            (!self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings());
    });
    self.hasDataverses = ko.pureComputed(function() {
        return self.dataverses().length > 0;
    });
    self.showNotFound = ko.pureComputed(function() {
        return self.savedDatasetDoi() && self.loadedDatasets() && !self.datasetWasFound();
    });
    self.showSubmitDataset = ko.pureComputed(function() {
        return self.nodeHasAuth() && self.connected() && self.userIsOwner();
    });
    self.enableSubmitDataset = ko.pureComputed(function() {
        return !self.submitting() && self.dataverseHasDatasets() &&
            self.savedDatasetDoi() !== self.selectedDatasetDoi();
    });

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

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
        self.changeMessage(self.messages.userSettingsError, 'text-warning');
        Raven.captureMessage('Could not GET dataverse settings', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });
}
/**
 * Update the view model from data returned from the server.
 */

ViewModel.prototype.updateFromData = function(data) {
    var self = this;
    self.urls(data.urls);
    self.ownerName(data.ownerName);
    self.nodeHasAuth(data.nodeHasAuth);
    self.userHasAuth(data.userHasAuth);
    self.userIsOwner(data.userIsOwner);

    if (self.nodeHasAuth()) {
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

ViewModel.prototype.setInfo = function() {
    var self = this;
    self.submitting(true);
    return osfHelpers.postJSON(
        self.urls().set,
        ko.toJS({
            dataverse: {
                alias: self.selectedDataverseAlias
            },
            dataset: {
                doi: self.selectedDatasetDoi
            }
        })
    ).done(function() {
        self.submitting(false);
        self.savedDataverseAlias(self.selectedDataverseAlias());
        self.savedDataverseTitle(self.selectedDataverseTitle());
        self.savedDatasetDoi(self.selectedDatasetDoi());
        self.savedDatasetTitle(self.selectedDatasetTitle());
        self.datasetWasFound(true);
        self.changeMessage(self.messages.setInfoSuccess, 'text-success');
    }).fail(function(xhr, textStatus, error) {
        self.submitting(false);
        var errorMessage = (xhr.status === 410) ? self.messages.datasetDeaccessioned :
            (xhr.status = 406) ? self.messages.forbiddenCharacters : self.messages.setDatasetError;
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
ViewModel.prototype.findDataset = function() {
    var self = this;
    for (var i in self.datasets()) {
        if (self.datasets()[i].doi === self.savedDatasetDoi()) {
            self.datasetWasFound(true);
            return;
        }
    }
};

ViewModel.prototype.getDatasets = function() {
    var self = this;
    self.datasets([]);
    self.loadedDatasets(false);
    return osfHelpers.postJSON(
        self.urls().getDatasets,
        ko.toJS({
            alias: self.selectedDataverseAlias
        })
    ).done(function(response) {
        self.datasets(response.datasets);
        self.loadedDatasets(true);
        self.selectedDatasetDoi(self.savedDatasetDoi());
        self.findDataset();
    }).fail(function(xhr, status, error) {
        self.changeMessage(self.messages.getDatasetsError, 'text-danger');
        Raven.captureMessage('Could not GET datasets', {
            url: self.urls().getDatasets,
            textStatus: status,
            error: error
        });
    });
};

ViewModel.prototype.authorizeNode = function() {
    var self = this;
    return osfHelpers.putJSON(
        self.urls().importAuth, {}
    ).done(function(response) {
        self.updateFromData(response.result);
        self.changeMessage(self.messages.importAuthSuccess, 'text-success', 3000);
    }).fail(function(xhr, status, error) {
        self.changeMessage(self.messages.importAuthError, 'text-danger');
        Raven.captureMessage('Could not import Dataverse node auth', {
            url: self.urls().importAuth,
            textStatus: status,
            error: error
        });
    });
};

/** Send POST request to authorize Dataverse */
ViewModel.prototype.sendAuth = function() {
    var self = this;
    return osfHelpers.postJSON(
        self.urls().create,
        ko.toJS({api_token: self.apiToken})
    ).done(function() {
        // User now has auth
        self.authorizeNode();
    }).fail(function(xhr) {
        var errorMessage = (xhr.status === 401) ? self.messages.authInvalid : self.messages.authError;
        self.changeMessage(errorMessage, 'text-danger');
    });
};

/**
 *  Send PUT request to import access token from user profile.
 */
ViewModel.prototype.importAuth = function() {
    var self = this;
    bootbox.confirm({
        title: 'Link to Dataverse Account?',
        message: self.messages.confirmImportAuth(),
        callback: function(confirmed) {
            if (confirmed) {
                self.authorizeNode();
            }
        }
    });
};

ViewModel.prototype.clickDeauth = function() {
    var self = this;

    function sendDeauth() {
        return $.ajax({
            url: self.urls().deauthorize,
            type: 'DELETE'
        }).done(function() {
            self.nodeHasAuth(false);
            self.userIsOwner(false);
            self.connected(false);
            self.changeMessage(self.messages.deauthSuccess, 'text-success', 3000);
        }).fail(function() {
            self.changeMessage(self.messages.deauthError, 'text-danger');
        });
    }

    bootbox.confirm({
        title: 'Deauthorize?',
        message: self.messages.confirmNodeDeauth(),
        callback: function(confirmed) {
            if (confirmed) {
                sendDeauth();
            }
        }
    });
};

/** Change the flashed status message */
ViewModel.prototype.changeMessage = function(text, css, timeout) {
    var self = this;
    if (typeof text === 'function') {
        text = text();
    }
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
