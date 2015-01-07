webpackJsonp([26],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

	var DataverseUserConfig = __webpack_require__(41);

	// Endpoint for Dataverse user settings
	var url = '/api/v1/settings/dataverse/';
	// Start up the DataverseConfig manager
	DataverseUserConfig('#dataverseAddonScope', url);


/***/ },

/***/ 41:
/***/ function(module, exports, __webpack_require__) {

	/**
	* Module that controls the Dataverse user settings. Includes Knockout view-model
	* for syncing data.
	*/

	var ko = __webpack_require__(16);
	__webpack_require__(7);
	ko.punches.enableAll();
	var $ = __webpack_require__(14);
	var Raven = __webpack_require__(15);
	var bootbox = __webpack_require__(11);

	var language = __webpack_require__(74).Addons.dataverse;
	var osfHelpers = __webpack_require__(2);

	function ViewModel(url) {
	    var self = this;
	    self.userHasAuth = ko.observable(false);
	    self.dataverseUsername = ko.observable();
	    self.dataversePassword = ko.observable();
	    self.connected = ko.observable();
	    self.urls = ko.observable({});
	    // Whether the initial data has been loaded
	    self.loaded = ko.observable(false);

	    self.showDeleteAuth = ko.computed(function() {
	        return self.loaded() && self.userHasAuth();
	    });
	    self.showInputCredentials = ko.computed(function() {
	        return self.loaded() && (!self.userHasAuth() || !self.connected());
	    });
	    self.credentialsChanged = ko.computed(function() {
	        return self.userHasAuth() && !self.connected();
	    });

	    // Update above observables with data from the server
	    $.ajax({
	        url: url,
	        type: 'GET',
	        dataType: 'json'
	    }).done(function(response) {
	        var data = response.result;
	        self.userHasAuth(data.userHasAuth);
	        self.urls(data.urls);
	        self.loaded(true);
	        self.dataverseUsername(data.dataverseUsername);
	        self.connected(data.connected);
	    }).fail(function(xhr, textStatus, error) {
	        self.changeMessage(language.userSettingsError, 'text-warning');
	        Raven.captureMessage('Could not GET Dataverse settings', {
	            url: url,
	            textStatus: textStatus,
	            error: error
	        });
	    });

	    // Flashed messages
	    self.message = ko.observable('');
	    self.messageClass = ko.observable('text-info');

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
	            self.userHasAuth(true);
	            self.connected(true);
	            self.changeMessage(language.authSuccess, 'text-info', 5000);
	        }).fail(function(xhr, textStatus, error) {
	            var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
	            self.changeMessage(errorMessage, 'text-danger');
	            Raven.captureMessage('Could not authenticate with Dataverse', {
	                url: self.urls().create,
	                textStatus: textStatus,
	                error: error
	            });
	        });
	    };

	    /** Pop up confirm dialog for deleting user's credentials. */
	    self.deleteKey = function() {
	        bootbox.confirm({
	            title: 'Delete Dataverse Token?',
	            message: language.confirmUserDeauth,
	            callback: function(confirmed) {
	                if (confirmed) {
	                    sendDeauth();
	                }
	            }
	        });
	    };

	    /** Send DELETE request to deauthorize Dataverse */
	    function sendDeauth() {
	        return $.ajax({
	            url: self.urls().delete,
	            type: 'DELETE'
	        }).done(function() {
	            // Page must be refreshed to remove the list of authorized nodes
	            location.reload();

	            // KO logic. Uncomment if page ever doesn't need refreshing
	            // self.userHasAuth(false);
	            // self.connected(false);
	            // self.dataverseUsername('');
	            // self.dataversePassword('');
	            // self.changeMessage(language.deauthSuccess, 'text-info', 5000);
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

	function DataverseUserConfig(selector, url) {
	    // Initialization code
	    var self = this;
	    self.selector = selector;
	    self.url = url;
	    // On success, instantiate and bind the ViewModel
	    self.viewModel = new ViewModel(url);
	    osfHelpers.applyBindings(self.viewModel, '#dataverseAddonScope');
	}
	module.exports = DataverseUserConfig;


/***/ },

/***/ 74:
/***/ function(module, exports, __webpack_require__) {

	module.exports = {
	    // TODO
	    makePublic: null,
	    makePrivate: null,

	    Addons: {
	        dataverse: {
	            userSettingsError: 'Could not retrieve settings. Please refresh the page or ' +
	                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
	                'problem persists.',
	            confirmUserDeauth: 'Are you sure you want to unlink your Dataverse ' +
	                'account? This will revoke access to Dataverse for all ' +
	                'projects you have authorized.',
	            confirmNodeDeauth: 'Are you sure you want to unlink this Dataverse account? This will ' +
	                'revoke the ability to view, download, modify, and upload files ' +
	                'to studies on the Dataverse from the OSF. This will not remove your ' +
	                'Dataverse authorization from your <a href="/settings/addons/">user settings</a> ' +
	                'page.',
	            deauthError: 'Could not unlink Dataverse at this time.',
	            deauthSuccess: 'Unlinked your Dataverse account.',
	            authError: 'There was a problem connecting to the Dataverse.',
	            authInvalid: 'Your Dataverse username or password is invalid.',
	            authSuccess: 'Your Dataverse account was linked.',
	            studyDeaccessioned: 'This study has already been deaccessioned on the Dataverse ' +
	                'and cannot be connected to the OSF.',
	            forbiddenCharacters: 'This study cannot be connected due to forbidden characters ' +
	                'in one or more of the study\'s file names. This issue has been forwarded to our ' +
	                'development team.',
	            setStudyError: 'Could not connect to this study.',
	            widgetInvalid: 'The Dataverse credentials associated with ' +
	                'this node appear to be invalid.',
	            widgetError: 'There was a problem connecting to the Dataverse.'
	        },
	        dropbox: {
	            // Shown on clicking "Delete Access Token" for dropbox
	            confirmDeauth: 'Are you sure you want to delete your Dropbox access ' +
	                'key? This will revoke access to Dropbox for all projects you have ' +
	                'authorized.',
	            deauthError: 'Could not deauthorize Dropbox at this time',
	            deauthSuccess: 'Deauthorized Dropbox.'
	        },
	        // TODO
	        github: {

	        },
	        s3: {

	        }
	    }
	};


/***/ }

});