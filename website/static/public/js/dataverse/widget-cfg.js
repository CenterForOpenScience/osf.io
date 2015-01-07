webpackJsonp([27],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

	var DataverseWidget = __webpack_require__(44);

	var url = window.contextVars.node.urls.api + 'dataverse/widget/contents/';
	new DataverseWidget('#dataverseScope', url);


/***/ },

/***/ 44:
/***/ function(module, exports, __webpack_require__) {

	'use strict';
	var ko = __webpack_require__(16);
	__webpack_require__(7);
	var $ = __webpack_require__(14);
	var $osf = __webpack_require__(2);

	ko.punches.enableAll();
	var language = __webpack_require__(74).Addons.dataverse;

	function ViewModel(url) {
	    var self = this;
	    self.connected = ko.observable();
	    self.dataverse = ko.observable();
	    self.dataverseUrl = ko.observable();
	    self.study = ko.observable();
	    self.doi = ko.observable();
	    self.studyUrl = ko.observable('');
	    self.citation = ko.observable('');
	    self.loaded = ko.observable(false);

	    // Flashed messages
	    self.message = ko.observable('');
	    self.messageClass = ko.observable('text-info')

	    self.init = function() {
	        $.ajax({
	            url: url, type: 'GET', dataType: 'json',
	            success: function(response) {
	                var data = response.data;
	                self.connected(data.connected);
	                self.dataverse(data.dataverse);
	                self.dataverseUrl(data.dataverseUrl);
	                self.study(data.study);
	                self.doi(data.doi);
	                self.studyUrl(data.studyUrl);
	                self.citation(data.citation);
	                self.loaded(true);
	            },
	            error: function(xhr) {
	                self.loaded(true);
	                var errorMessage = (xhr.status === 403) ? language.widgetInvalid : language.widgetError;
	                self.changeMessage(errorMessage, 'text-danger');
	            }
	        });
	    };

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

	// Public API
	function DataverseWidget(selector, url) {
	    var self = this;
	    self.viewModel = new ViewModel(url);
	    $osf.applyBindings(self.viewModel, selector);
	    self.viewModel.init();
	}

	module.exports = DataverseWidget;


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