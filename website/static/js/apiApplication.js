/*
 *  Knockout views for the Developer application pages: List and Create/Edit pages.
 */


'use strict';

// TODO: Some of these may not be actually required. Dependency list ripped from profile view
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
require('knockout.validation');
require('knockout.punches');
ko.punches.enableAll();
require('knockout-sortable');

var $osf = require('./osfHelpers');
var koHelpers = require('./koHelpers');
require('js/objectCreateShim');


/*
 *  Store the data related to a single API application. Some vars should never be changed.
 */
var ApplicationData = function(data){
    var self = this;

    data = data || {};

    self.clientId = ko.observable(data.client_id || '');
    self.clientSecret = ko.observable(data.client_secret || '');
    self.reg_date = ko.observable(data.reg_date || '');

    self.owner = ko.observable(data.owner || '');
    self.name = ko.observable(data.name || '');
    self.description = ko.observable(data.description || '');
    self.homeUrl = ko.observable(data.home_url || '');
    self.callbackUrl = ko.observable(data.callback_url || '');

    // Unchanging properties
    self.detailUrl = data.links.html  || '';
    self.apiUrl = data.links.self  || '';

    // Serialize data for POST request
    self.serialize = function() {
        return {
            client_id: self.clientId(),
            client_secret: self.clientSecret(),
            owner: self.owner(),
            name: self.name(),
            description: self.description(),
            home_url: self.homeUrl(),
            callback_url: self.callbackUrl()
        }
    };
};


var ApplicationViewModel = function(urls) {
    // Read and update operations

    var self = this;
    self.content = ko.observable({});
    self.message = ko.observable();
    self.messageClass = ko.observable();

    self.detailUrl = urls.apiUrl;

    // TODO: Deal with detail page template being re-used when there is no detail view

    /////// Helper functions
    self.fetch = function (url) { // TODO: duplicated in ApplicationListViewModel
        $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json',
            // Enable CORS
            crossOrigin: true,
            xhrFields: {
                withCredentials: true
            },
            success: function (data) {
                var result;
                // Check return type to handle both list and detail views
                if (Array.isArray(data.data)){  // ES5 dependent
                    result = $.map(data.data, function (item) {
                        return new ApplicationData(item)
                    });
                } else if (data.data){
                    result = new ApplicationData(data.data);
                }

                self.content(result);
            },
            error: function (xhr, status, err) {
                $osf.growl('Error', 'Data not loaded. Please refresh the page and try ' +
                'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                'if the problem persists.', 'danger');

                Raven.captureMessage('Error fetching application data', {
                    url: url,
                    status: status,
                    error: err
                });
            }
        })
    };

    // TODO: duplicated from profile.js; clean up and consolidate
    self.changeMessage = function(text, css, timeout) {
        var self = this;
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(
                function() {
                    self.message('');
                    self.messageClass('text-info');
                },
                timeout
            );
        }
    };

    self.updateApplication = function () {
        var payload = self.content().serialize();
        $.ajax({
            type: 'PATCH',
            url: self.detailUrl,
            data: payload,
            dataType: 'json',
            // Enable CORS
            crossOrigin: true,
            xhrFields: {
                withCredentials: true
            },
            success: function (data) {
                // TODO: Perhaps also update form fields with request return values? (eg reflect html sanitization)
                self.changeMessage(
                    "Application data submitted",
                    "text-success",
                    5000);
            },
            error: function (xhr, status, err) {
                //  TODO: change error messages
                $osf.growl('Error', 'Could not send request. Please refresh the page and try ' +
                'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                'if the problem persists.', 'danger');

                Raven.captureMessage('Error updating instance', {
                    url: url,
                    status: status,
                    error: err
                });
            }
        });

        // TODO: Add success and failure functions- follow accountSettings.js as template and replace callbacks
        // TODO: replace osf helper with CORS request generator
    };


    // Code that gets called after object is initialized (must be called after fetch defined?)
    if (self.detailUrl){ // Support detail views
        self.fetch(self.detailUrl);
    }
};

/*
 * Fetch a list of applications associated with the given user.
 */
function ApplicationsListViewModel(urls) {
    var self = this;
    self.listUrl = urls.apiUrl;

    self.content = ko.observableArray();

    //////// Helper functions
    self.fetch = function (url) {
        $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json',
            // Enable CORS
            crossOrigin: true,
            xhrFields: {
                withCredentials: true
            },
            success: function (data) {
                var dataArray;
                // Check return type to handle both list and detail views
                if (Array.isArray(data.data)){  // ES5 dependent
                    dataArray = $.map(data.data, function (item) {
                        return new ApplicationData(item)
                    });
                } else if (data.data){
                    dataArray = new ApplicationData(data.data);
                }

                self.content(dataArray);
            },
            error: function (xhr, status, err) {
                $osf.growl('Error', 'Data not loaded. Please refresh the page and try ' +
                'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                'if the problem persists.', 'danger');

                Raven.captureMessage('Error fetching application data', {
                    url: url,
                    status: status,
                    error: err
                });
            }
        })
    };

    self.fetch(self.listUrl); // TODO: Reorg code

    self.deleteApplication = function (appData) {
        // Delete a single application
        // TODO: Add confirmation dialog- modal
        $.ajax({
            type: 'DELETE',
            url: appData.apiUrl,
            dataType: 'json',
            // Enable CORS
            crossOrigin: true,
            xhrFields: {
                withCredentials: true
            },
            success: function (data) {
                self.content.destroy(appData);
            },
            error: function () {
            }
        });
    };
}


var ApplicationsList = function(selector, urls, modes) {
    this.viewModel = new ApplicationsListViewModel(urls, modes);
    $osf.applyBindings(this.viewModel, selector);
};

var ApplicationDetail = function(selector, urls, modes) {
    this.viewModel = new ApplicationViewModel(urls, modes);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    ApplicationsList: ApplicationsList,
    ApplicationDetail: ApplicationDetail
};
