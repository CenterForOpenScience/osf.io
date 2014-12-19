/**
* Module that controls the {{cookiecutter.full_name}} node settings. Includes Knockout view-model
* for syncing data.
*/

var ko = require('knockout');
var bootbox = require('bootbox');
require('knockout-punches');
var osfHelpers = require('osfHelpers');
var language = require('osfLanguage');

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

    self.savedStudyUrl = ko.computed(function() {
        return (self.urls()) ? self.urls().studyPrefix + self.savedStudyHdl() : null;
    });
    self.savedDataverseUrl = ko.computed(function() {
        return (self.urls()) ? self.urls().dataversePrefix + self.savedDataverseAlias() : null;
    });

    self.selectedDataverseAlias = ko.observable();
    self.selectedStudyHdl = ko.observable();
    self.selectedDataverseTitle = ko.computed(function() {
        for (var i=0; i < self.dataverses().length; i++) {
            var data = self.dataverses()[i];
            if (data.alias === self.selectedDataverseAlias()) {
                return data.title;
            }
        }
        return null;
    });
    self.selectedStudyTitle = ko.computed(function() {
        for (var i=0; i < self.studies().length; i++) {
            var data = self.studies()[i];
            if (data.hdl === self.selectedStudyHdl()) {
                return data.title;
            }
        }
        return null;
    });
    self.dataverseHasStudies = ko.computed(function() {
        return self.studies().length > 0;
    });

    self.showStudySelect = ko.computed(function() {
        return self.loadedStudies() && self.dataverseHasStudies();
    });
    self.showNoStudies = ko.computed(function() {
        return self.loadedStudies() && !self.dataverseHasStudies();
    });
    self.showLinkedStudy = ko.computed(function() {
        return self.savedStudyHdl();
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
    self.hasBadStudies = ko.computed(function() {
        return self.badStudies().length > 0;
    });
    self.showNotFound = ko.computed(function() {
        return self.savedStudyHdl() && self.loadedStudies() && !self.studyWasFound();
    });
    self.showSubmitStudy = ko.computed(function() {
        return self.nodeHasAuth() && self.connected() && self.userIsOwner();
    });
    self.enableSubmitStudy = ko.computed(function() {
        return !self.submitting() && self.dataverseHasStudies() &&
            self.savedStudyHdl() !== self.selectedStudyHdl();
    });

    /**
        * Update the view model from data returned from the server.
        */

    self.updateFromData = function(data) {
        self.urls(data.urls);
        self.dataverseUsername(data.dataverseUsername);
        self.ownerName(data.ownerName);
        self.nodeHasAuth(data.nodeHasAuth);
        self.userHasAuth(data.userHasAuth);
        self.userIsOwner(data.userIsOwner);

        if (self.nodeHasAuth()){
            self.dataverses(data.dataverses);
            self.savedDataverseAlias(data.savedDataverse.alias);
            self.savedDataverseTitle(data.savedDataverse.title);
            self.selectedDataverseAlias(data.savedDataverse.alias);
            self.savedStudyHdl(data.savedStudy.hdl);
            self.savedStudyTitle(data.savedStudy.title);
            self.connected(data.connected);
            if (self.userIsOwner()) {
                self.getStudies(); // Sets studies, selectedStudyHdl
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
                study: {hdl: self.selectedStudyHdl}
            })
        ).done(function() {
            self.submitting(false);
            self.savedDataverseAlias(self.selectedDataverseAlias());
            self.savedDataverseTitle(self.selectedDataverseTitle());
            self.savedStudyHdl(self.selectedStudyHdl());
            self.savedStudyTitle(self.selectedStudyTitle());
            self.studyWasFound(true);
            self.changeMessage('Settings updated.', 'text-success', 5000);
        }).fail(function(xhr, textStatus, error) {
            self.submitting(false);
            var errorMessage = (xhr.status === 410) ? language.studyDeaccessioned :
                (xhr.status = 406) ? language.forbiddenCharacters : language.setStudyError;
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
    self.findStudy = function() {
        for (var i in self.studies()) {
            if (self.studies()[i].hdl === self.savedStudyHdl()) {
                self.studyWasFound(true);
                return;
            }
        }
    };

    self.getStudies = function() {
        self.studies([]);
        self.badStudies([]);
        self.loadedStudies(false);
        return osfHelpers.postJSON(
            self.urls().getStudies,
            ko.toJS({alias: self.selectedDataverseAlias})
        ).done(function(response) {
            self.studies(response.studies);
            self.badStudies(response.badStudies);
            self.loadedStudies(true);
            self.selectedStudyHdl(self.savedStudyHdl());
            self.findStudy();
        }).fail(function() {
            self.changeMessage('Could not load studies', 'text-danger');
        });
    };

    /** Send POST request to authorize Dataverse */
    self.sendAuth = function() {
        return osfHelpers.postJSON(
            self.urls().create,
            ko.toJS({
                dataverse_username: self.dataverseUsername,
                dataverse_password: self.dataversePassword
            })
        ).done(function() {
            // User now has auth
            authorizeNode();
        }).fail(function(xhr) {
            var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
        });
    };

    /**
        * Send PUT request to import access token from user profile.
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
