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
    self.dataverseUsername = ko.observable();
    self.dataversePassword = ko.observable();

    self.ownerName = ko.observable();
    self.nodeHasAuth = ko.observable(false);
    self.userHasAuth = ko.observable(false);
    self.userIsOwner = ko.observable(false);
    self.connected = ko.observable(false);
    self.loadedSettings = ko.observable(false);
    self.loadedStudies = ko.observable(false);
    self.submitting = ko.observable(false);

    self.dataverses = ko.observableArray([]);
    self.studies = ko.observableArray([]);
    self.badStudies = ko.observableArray([]);

    self.savedStudyHdl = ko.observable();
    self.savedStudyTitle = ko.observable();
    self.savedDataverseAlias = ko.observable();
    self.savedDataverseTitle = ko.observable();
    self.studyWasFound = ko.observable(false);

    self.messages = {
        userSettingsError: ko.pureComputed(function() {
            return 'Could not retrieve settings. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        confirmNodeDeauth: ko.pureComputed(function() {
            return 'Are you sure you want to unlink this Dataverse account? This will ' +
                'revoke the ability to view, download, modify, and upload files ' +
                'to studies on the Dataverse from the OSF. This will not remove your ' +
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
            return 'Your Dataverse username or password is invalid.';
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
        studyDeaccessioned: ko.pureComputed(function() {
            return 'This study has already been deaccessioned on the Dataverse ' +
                'and cannot be connected to the OSF.';
        }),
        forbiddenCharacters: ko.pureComputed(function() {
            return 'This study cannot be connected due to forbidden characters ' +
                'in one or more of the study\'s file names. This issue has been forwarded to our ' +
                'development team.';
        }),
        setInfoSuccess: ko.pureComputed(function() {
            var filesUrl = window.contextVars.node.urls.web + 'files/';
            return 'Successfully linked study \'' + self.savedStudyTitle() + '\'. Go to the <a href="' +
                filesUrl + '">Files page</a> to view your content.';
        }),
        setStudyError: ko.pureComputed(function() {
            return 'Could not connect to this study. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        getStudiesError: ko.pureComputed(function() {
            return 'Could not load studies. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        })
    };

    self.savedStudyUrl = ko.pureComputed(function() {
        return (self.urls()) ? self.urls().studyPrefix + self.savedStudyHdl() : null;
    });
    self.savedDataverseUrl = ko.pureComputed(function() {
        return (self.urls()) ? self.urls().dataversePrefix + self.savedDataverseAlias() : null;
    });

    self.selectedDataverseAlias = ko.observable();
    self.selectedStudyHdl = ko.observable();
    self.selectedDataverseTitle = ko.pureComputed(function() {
        for (var i = 0; i < self.dataverses().length; i++) {
            var data = self.dataverses()[i];
            if (data.alias === self.selectedDataverseAlias()) {
                return data.title;
            }
        }
        return null;
    });
    self.selectedStudyTitle = ko.pureComputed(function() {
        for (var i = 0; i < self.studies().length; i++) {
            var data = self.studies()[i];
            if (data.hdl === self.selectedStudyHdl()) {
                return data.title;
            }
        }
        return null;
    });
    self.dataverseHasStudies = ko.pureComputed(function() {
        return self.studies().length > 0;
    });

    self.showStudySelect = ko.pureComputed(function() {
        return self.loadedStudies() && self.dataverseHasStudies();
    });
    self.showNoStudies = ko.pureComputed(function() {
        return self.loadedStudies() && !self.dataverseHasStudies();
    });
    self.showLinkedStudy = ko.pureComputed(function() {
        return self.savedStudyHdl();
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
    self.hasBadStudies = ko.pureComputed(function() {
        return self.badStudies().length > 0;
    });
    self.showNotFound = ko.pureComputed(function() {
        return self.savedStudyHdl() && self.loadedStudies() && !self.studyWasFound();
    });
    self.showSubmitStudy = ko.pureComputed(function() {
        return self.nodeHasAuth() && self.connected() && self.userIsOwner();
    });
    self.enableSubmitStudy = ko.pureComputed(function() {
        return !self.submitting() && self.dataverseHasStudies() &&
            self.savedStudyHdl() !== self.selectedStudyHdl();
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
    self.dataverseUsername(data.dataverseUsername);
    self.ownerName(data.ownerName);
    self.nodeHasAuth(data.nodeHasAuth);
    self.userHasAuth(data.userHasAuth);
    self.userIsOwner(data.userIsOwner);

    if (self.nodeHasAuth()) {
        self.dataverses(data.dataverses);
        self.savedDataverseAlias(data.savedDataverse.alias);
        self.savedDataverseTitle(data.savedDataverse.title);
        self.selectedDataverseAlias(data.savedDataverse.alias);
        self.savendStudyHdl(data.savedStudy.hdl);
        self.savedStudyTitle(data.savedStudy.title);
        self.connected(data.connected);
        if (self.userIsOwner()) {
            self.getStudies(); // Sets studies, selectedStudyHdl
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
            study: {
                hdl: self.selectedStudyHdl
            }
        })
    ).done(function() {
        self.submitting(false);
        self.savedDataverseAlias(self.selectedDataverseAlias());
        self.savedDataverseTitle(self.selectedDataverseTitle());
        self.savedStudyHdl(self.selectedStudyHdl());
        self.savedStudyTitle(self.selectedStudyTitle());
        self.studyWasFound(true);
        self.changeMessage(self.messages.setInfoSuccess, 'text-success');
    }).fail(function(xhr, textStatus, error) {
        self.submitting(false);
        var errorMessage = (xhr.status === 410) ? self.messages.studyDeaccessioned :
            (xhr.status = 406) ? self.messages.forbiddenCharacters : self.messages.setStudyError;
 self.changeMessage(errorMessage, 'text-danger');
        Raven.captureMessage('Could not authenticate with Dataverse', {
            url: self.urls().set,
            textStatus: textStatus,
            error: error
        });
    });
};

/**
 * Looks for study in list of studies when first loaded.
 * This prevents an additional request to the server, but requires additional logic.
 */
ViewModel.prototype.findStudy = function() {
    var self = this;
    for (var i in self.studies()) {
        if (self.studies()[i].hdl === self.savedStudyHdl()) {
            self.studyWasFound(true);
            return;
        }
    }
};

ViewModel.prototype.getStudies = function() {
    var self = this;
    self.studies([]);
    self.badStudies([]);
    self.loadedStudies(false);
    return osfHelpers.postJSON(
        self.urls().getStudies,
        ko.toJS({
            alias: self.selectedDataverseAlias
        })
    ).done(function(response) {
        self.studies(response.studies);
        self.badStudies(response.badStudies);
        self.loadedStudies(true);
        self.selectedStudyHdl(self.savedStudyHdl());
        self.findStudy();
    }).fail(function() {
        self.changeMessage(self.messages.getStudiesError, 'text-danger');
    });
};

ViewModel.prototype.authorizeNode = function() {
    var self = this;
    return osfHelpers.putJSON(
        self.urls().importAuth, {}
    ).done(function(response) {
        self.updateFromData(response.result);
        self.changeMessage(self.messages.importAuthSuccess, 'text-success', 3000);
    }).fail(function() {
        self.changeMessage(self.messages.importAuthError, 'text-danger');
    });
};

/** Send POST request to authorize Dataverse */
ViewModel.prototype.sendAuth = function() {
    var self = this;
    return osfHelpers.postJSON(
        self.urls().create,
        ko.toJS({
            dataverse_username: self.dataverseUsername,
            dataverse_password: self.dataversePassword
        })
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
