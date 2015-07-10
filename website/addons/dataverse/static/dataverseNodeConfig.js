/**
 * Module that controls the Dataverse node settings. Includes Knockout view-model
 * for syncing data.
 */

var ko = require('knockout');
var bootbox = require('bootbox');
require('knockout.punches');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

var $modal = $('#dataverseInputCredentials');

ko.punches.enableAll();

function ViewModel(url) {
    var self = this;
    const otherString = 'Other (Please Specify)';

    self.addonName = 'Dataverse';
    self.url = url;
    self.urls = ko.observable();
    self.apiToken = ko.observable();

    self.ownerName = ko.observable();
    self.nodeHasAuth = ko.observable(false);
    self.userHasAuth = ko.observable(false);
    self.userIsOwner = ko.observable(false);
    self.validCredentials = ko.observable(false);
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

    self.accounts = ko.observable([]);
    self.hosts = ko.observableArray([]);
    self.selectedHost = ko.observable();    // Host specified in select element
    self.customHost = ko.observable();      // Host specified in input element
    self.savedHost = ko.observable();       // Configured host

    // Designated host, specified from select or input element
    self.host = ko.pureComputed(function() {
        return self.useCustomHost() ? self.customHost() : self.selectedHost();
    });
    // Hosts visible in select element. Includes presets and "Other" option
    self.visibleHosts = ko.pureComputed(function() {
        return self.hosts().concat([otherString]);
    });
    // Whether to use select element or input element for host designation
    self.useCustomHost = ko.pureComputed(function() {
        return self.selectedHost() === otherString;
    });
    self.showApiTokenInput = ko.pureComputed(function() {
        return Boolean(self.selectedHost());
    });
    self.tokenUrl = ko.pureComputed(function() {
       return self.host() ? 'https://' + self.host() + '/account/apitoken' : null;
    });
    self.savedHostUrl = ko.pureComputed(function() {
        return 'https://' + self.savedHost();
    });

    self.messages = {
        userSettingsError: ko.pureComputed(function() {
            return 'Could not retrieve settings. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        confirmDeauth: ko.pureComputed(function() {
            return 'Are you sure you want to remove this ' + self.addonName + ' authorization?';
        }),
        confirmAuth: ko.pureComputed(function() {
            return 'Are you sure you want to authorize this project with your ' + self.addonName + ' access token?';
        }),
        deauthorizeSuccess: ko.pureComputed(function() {
            return 'Deauthorized ' + self.addonName + '.';
        }),
        deauthorizeFail: ko.pureComputed(function() {
            return 'Could not deauthorize because of an error. Please try again later.';
        }),
        authInvalid: ko.pureComputed(function() {
            return 'The API token provided for ' + self.host() + ' is invalid.';
        }),
        authError: ko.pureComputed(function() {
            return 'There was a problem connecting to the Dataverse. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        tokenImportSuccess: ko.pureComputed(function() {
            return 'Successfully imported access token from profile.';
        }),
        tokenImportError: ko.pureComputed(function() {
            return 'Error occurred while importing access token.';
        }),
        updateAccountsError: ko.pureComputed(function() {
            return 'Could not retrieve ' + self.addonName + ' account list at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        }),
        datasetDeaccessioned: ko.pureComputed(function() {
            return 'This dataset has already been deaccessioned on Dataverse ' +
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
        return self.nodeHasAuth() && !self.validCredentials();
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
        return self.nodeHasAuth() && self.validCredentials() && self.userIsOwner();
    });
    self.enableSubmitDataset = ko.pureComputed(function() {
        return !self.submitting() && self.dataverseHasDatasets() &&
            self.savedDatasetDoi() !== self.selectedDatasetDoi();
    });

    self.showSettings = ko.pureComputed(function() {
        return self.nodeHasAuth() && self.validCredentials();
    });
    self.showImport = ko.pureComputed(function() {
        return self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
    });
    self.showTokenCreateButton = ko.pureComputed(function() {
        return !self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
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
    self.hosts(data.hosts);

    if (self.nodeHasAuth()) {
        self.savedHost(data.dataverseHost);
        self.dataverses(data.dataverses);
        self.savedDataverseAlias(data.savedDataverse.alias);
        self.savedDataverseTitle(data.savedDataverse.title);
        self.selectedDataverseAlias(data.savedDataverse.alias);
        self.savedDatasetDoi(data.savedDataset.doi);
        self.savedDatasetTitle(data.savedDataset.title);
        self.validCredentials(data.connected);
        if (self.userIsOwner()) {
            self.getDatasets(); // Sets datasets, selectedDatasetDoi
        }
    }
};

/** Reset all fields from Dataverse host selection modal */
ViewModel.prototype.clearModal = function() {
    var self = this;
    self.message('');
    self.messageClass('text-info');
    self.apiToken(null);
    self.selectedHost(null);
    self.customHost(null);
};

ViewModel.prototype.setInfo = function() {
    var self = this;
    self.submitting(true);
    return $osf.postJSON(
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
    return $osf.postJSON(
        self.urls().getDatasets,
        ko.toJS({
            alias: self.selectedDataverseAlias
        })
    ).done(function(response) {
        // Don't update if another Dataverse has been selected
        if (response.alias === self.selectedDataverseAlias()) {
            self.datasets(response.datasets);
            self.loadedDatasets(true);
            self.selectedDatasetDoi(self.savedDatasetDoi());
            self.findDataset();
        }
    }).fail(function(xhr, status, error) {
        self.changeMessage(self.messages.getDatasetsError, 'text-danger');
        Raven.captureMessage('Could not GET datasets', {
            url: self.urls().getDatasets,
            textStatus: status,
            error: error
        });
    });
};

/** Send POST request to authorize Dataverse */
ViewModel.prototype.sendAuth = function() {
    var self = this;
    var url = self.urls().create;
    return $osf.postJSON(
        url,
        ko.toJS({
            host: self.host,
            api_token: self.apiToken
        })
    ).done(function() {
        self.clearModal();
        $modal.modal('hide');
        self.importAuth();
    }).fail(function(xhr, textStatus, error) {
        var errorMessage = (xhr.status === 401) ? self.messages.authInvalid : self.messages.authError;
        self.changeMessage(errorMessage, 'text-danger');
        Raven.captureMessage('Could not authenticate with Dataverse', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });
};

ViewModel.prototype.fetchAccounts = function() {
    var self = this;
    var ret = $.Deferred();
    var request = $.get(self.urls().accounts);
    request.then(function(data) {
        ret.resolve(data.accounts);
    });
    request.fail(function(xhr, textStatus, error) {
        self.changeMessage(self.messages.updateAccountsError(), 'text-warning');
        Raven.captureMessage('Could not GET ' + self.addonName + ' accounts for user', {
            url: self.url,
            textStatus: textStatus,
            error: error
        });
        ret.reject(xhr, textStatus, error);
    });
    return ret.promise();
};

ViewModel.prototype.updateAccounts = function() {
    var self = this;
    return self.fetchAccounts()
        .done(function(accounts) {
            self.accounts(
                $.map(accounts, function(account) {
                    return {
                        name: account.display_name,
                        id: account.id
                    };
                })
            );
        });
};

ViewModel.prototype.onImportSuccess = function(response) {
    var self = this;
    var msg = response.message || self.messages.tokenImportSuccess();
    // Update view model based on response
    self.changeMessage(msg, 'text-success', 3000);
    self.updateFromData(response.result);
};

ViewModel.prototype.onImportError = function(xhr, status, error) {
    var self = this;
    self.changeMessage(self.messages.tokenImportError(), 'text-danger');
    Raven.captureMessage('Failed to import ' + self.addonName + ' access token.', {
        xhr: xhr,
        status: status,
        error: error
    });
};

/**
 * Allows a user to create an access token from the nodeSettings page
 */
ViewModel.prototype.connectAccount = function() {
    var self = this;

    window.oauthComplete = function(res) {
        // Update view model based on response
        self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
        self.importAuth.call(self);
    };
    window.open(self.urls().auth);
};

ViewModel.prototype.connectExistingAccount = function(account_id) {
    var self = this;

    return $osf.putJSON(
        self.urls().importAuth, {
            external_account_id: account_id
        }
    ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
};

/**
 *  Send PUT request to import access token from user profile.
 */
ViewModel.prototype.importAuth = function() {
    var self = this;
    self.updateAccounts()
        .then(function(){
            if (self.accounts().length > 1) {
                bootbox.prompt({
                    title: 'Choose ' + self.addonName + ' Access Token to Import',
                    inputType: 'select',
                    inputOptions: ko.utils.arrayMap(
                        self.accounts(),
                        function(item) {
                            return {
                                text: item.name,
                                value: item.id
                            };
                        }
                    ),
                    value: self.accounts()[0].id,
                    callback: function(accountId) {
                        if (accountId) {
                            self.connectExistingAccount.call(self, (accountId));
                        }
                    }
                });
            } else {
                bootbox.confirm({
                    title: 'Import ' + self.addonName + ' Access Token?',
                    message: self.messages.confirmAuth(),
                    callback: function(confirmed) {
                        if (confirmed) {
                            self.connectExistingAccount.call(self, (self.accounts()[0].id));
                        }
                    }
                });
            }
        });
};

/**
 * Send DELETE request to deauthorize this node.
 */
ViewModel.prototype._deauthorizeConfirm = function() {
    var self = this;
    var request = $.ajax({
        url: self.urls().deauthorize,
        type: 'DELETE'
    });
    request.done(function() {
        // Update observables
        self.nodeHasAuth(false);
        self.clearModal();
        self.changeMessage(self.messages.deauthorizeSuccess(), 'text-warning', 3000);
    });
    request.fail(function(xhr, textStatus, error) {
        self.changeMessage(self.messages.deauthorizeFail(), 'text-danger');
        Raven.captureMessage('Could not deauthorize ' + self.addonName + ' account from node', {
            url: self.urls().deauthorize,
            textStatus: textStatus,
            error: error
        });
    });
    return request;
};

/** Pop up a confirmation to deauthorize addon from this node.
 *  Send DELETE request if confirmed.
 */
ViewModel.prototype.deauthorize = function() {
    var self = this;
    bootbox.confirm({
        title: 'Deauthorize ' + self.addonName + '?',
        message: self.messages.confirmDeauth(),
        callback: function(confirmed) {
            if (confirmed) {
                self._deauthorizeConfirm();
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
    $osf.applyBindings(self.viewModel, '#dataverseScope');
}
module.exports = DataverseNodeConfig;
