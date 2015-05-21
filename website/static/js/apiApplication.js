/*
 *  Knockout views for the Developer application pages: List and Create/Edit pages.
 */


'use strict';

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
function ApplicationData(data){
    var self = this;

    self.clientId = ko.observable(data.client_id);
    self.clientSecret = ko.observable(data.client_secret);
    self.reg_date = ko.observable(data.reg_date);

    self.owner = ko.observable(data.owner);
    self.ownerName = ko.observable(data.name);
    self.description = ko.observable(data.description);
    self.homeUrl = ko.observable(data.home_url);
    self.callbackUrl = ko.observable(data.callback_url);

    // Unchanging properties
    self.detailUrl = data.links.html;
    self.apiUrl = data.links.self;

    // Serialize data for POST request
    self.serialize = function() {
        return {
            client_id: self.clientId(),
            client_secret: self.clientSecret(),
            owner: self.owner(),
            name: self.ownerName(),
            description: self.description(),
            home_url: self.home_url(),
            callback_url: self.callback_url()
        }
    };


}


var ApplicationViewModel = function() {
    // Read and update operations

    var self = this;
    self.content = ko.observable();

    self.fetch(detailUrl);

    /////// Helper functions
    self.fetch = function (url) {
        $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json',
            success: function (data) {
                self.content(new ApplicationData(data.data));
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

    self.update = function (appData) {
        var payload = appData.serialize();
        var request = $osf.postJSON(self.detailUrl, payload,
            function(){console.log('success callback fired')}
        );

        // TODO: Add success and failure functions- follow accountSettings.js as template and replace callbacks


    };
};

/*
 * Fetch a list of applications associated with the given user.
 */
function ApplicationsListViewModel(urls) {
    var self = this;
    self.listUrl = urls.appListUrl;

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
                var dataArray = $.map(data.data, function (item) {
                    return new ApplicationData(item)
                });
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

    self.fetch(self.listUrl);

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

module.exports = {
    ApplicationsList: ApplicationsList
};
