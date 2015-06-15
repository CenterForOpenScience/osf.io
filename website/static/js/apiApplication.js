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
 *  Store the data related to a single API application
 */
var ApplicationData = function (data){
    var self = this;
    self.clientId = ko.observable();
    self.clientSecret = ko.observable();
    self.create_date = ko.observable();

    self.owner = ko.observable();
    self.name = ko.observable();
    self.description = ko.observable();
    self.homeUrl = ko.observable();
    self.callbackUrl = ko.observable();

    // Unchanging properties
    self.detailUrl = ko.observable();
    self.apiUrl = ko.observable();

    // Load in data
    if (data){
        self.fromJSON(data)
    }
};

// Serialize data for POST request
ApplicationData.prototype.toJSON = function () {
    var self = this;
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

// Load data from JSON
ApplicationData.prototype.fromJSON = function (data) {
    var self = this;
    data = data || {};
    self.clientId(data.client_id);
    self.clientSecret(data.client_secret);
    self.create_date(data.create_date);

    self.owner(data.owner);
    self.name(data.name);
    self.description(data.description);
    self.homeUrl(data.home_url);
    self.callbackUrl(data.callback_url);

    self.detailUrl(data.links.html);
    self.apiUrl(data.links.self);
};


var applicationFetch = function (url) { // Function shared by list and detail ViewModels
    var self = this;
    var request = $osf.ajaxJSON("GET", url, {isCors:true});

    request.done(function (data) {
        var result;
        // Check return type to handle both list and detail views
        if (Array.isArray(data.data)) {  // ES5 dependent
            result = $.map(data.data, function (item) {
                return new ApplicationData(item)
            });
        } else if (data.data) {
            result = new ApplicationData(data.data);
        }
        self.content(result);
    });

    request.fail(function (xhr, status, err) {
        $osf.growl('Error', 'Data not loaded. Please refresh the page and try ' +
            'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
            'if the problem persists.', 'danger');

        Raven.captureMessage('Error fetching application data', {
            url: url,
            status: status,
            error: err
        })
    });
};


/*
 * Create (or update) the data for a single application. On creation, page seamlessly transitions to acting
 * like an update page.
 */
var ApplicationViewModel = function (urls) {
    // Read and update operations

    var self = this;
    self.content = ko.observable(new ApplicationData);
    self.message = ko.observable();
    self.messageClass = ko.observable();

    self.dataUrl = urls.dataUrl; // Use for editing existing instances
    self.submitUrl = urls.submitUrl; // Use for creating new instances

    if (self.dataUrl){ // Support detail views
        self.fetch(self.dataUrl);
    }
};

ApplicationViewModel.prototype.fetch = applicationFetch;

ApplicationViewModel.prototype.updateApplication = function () {
    // Update an existing application (has a known dataUrl) via PATCH request
    var self = this;

    var url = self.dataUrl;

    var payload = self.content().toJSON();

    var request = $osf.ajaxJSON("PATCH", url, {isCors: true, data: payload});

    request.done(function (data) {
        self.content().fromJSON(data.data);  // Update the data with what request returns- reflect server side cleaning
        self.changeMessage(
            "Application data submitted",  // TODO: Some pages (eg profile) show a one-line message for updates; others use a growl box. Current best practices?
            "text-success",
            5000);
    });

    request.fail(function (xhr, status, err) {
            $osf.growl('Error', 'Could not send request. Please refresh the page and try ' +
            'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
            'if the problem persists.', 'danger');

            Raven.captureMessage('Error updating instance', {
                url: url,
                status: status,
                error: err
            });
    });
};

ApplicationViewModel.prototype.createApplication = function () {
    // Create a new application instance via POST request (when model has submitUrl, but no dataUrl)
    var self = this;
    var payload = self.content().toJSON();

    var url = self.submitUrl;

    var request = $osf.ajaxJSON('POST', url, {isCors: true, data: payload});

    request.done(function (data) {
        self.content().fromJSON(data.data);  // Update the data with what request returns- reflect server side cleaning

        // TODO: Window.location refreshes anyway, rendering some of this KO.js code possibly unnecessary. Either reload seamlessly in-page, or refresh; doing both is architecturally awkward.
        // pushState is an alternative (and used in OSF search page), but not supported uniformly in older browsers
        $osf.growl('Application created', 'Application created!', 'success');


        // Update behaviors: after creation, this should look & act like a detail view for existing application
        window.location = data.data.links.html; // Update address bar to show new detail page
        self.dataUrl = data.data.links.self;
    });

    request.fail(function (xhr, status, err) {
        $osf.growl('Error', 'Could not send request. Please refresh the page and try ' +
        'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
        'if the problem persists.', 'danger');

        Raven.captureMessage('Error updating instance', {
            url: url,
            status: status,
            error: err
        });
    });
};

ApplicationViewModel.prototype.changeMessage = function (text, css, timeout) {
    // TODO: Some of this overlaps heavily with profile.js
    var self = this;
    self.message(text);
    var cssClass = css || 'text-info';
    self.messageClass(cssClass);
    if (timeout) {
        // Reset message after timeout period
        setTimeout(
            function () {
                self.message('');
                self.messageClass('text-info');
            },
            timeout
        );
    }
};

/*
 * Fetch a list of applications associated with the given user.
 */
var ApplicationsListViewModel= function (urls) {
    var self = this;
    self.listUrl = urls.dataUrl;
    self.content = ko.observableArray();

    self.fetch(self.listUrl);
};

ApplicationsListViewModel.prototype.fetch = applicationFetch;

ApplicationsListViewModel.prototype.deleteApplication = function (appData) {
    // Delete a single application
    var self = this;
    var url = appData.apiUrl();

    bootbox.confirm({
        title: 'De-register application?',
        message: 'Are you sure you want to de-register this application and revoke all access tokens? This cannot be reversed.',
        callback: function (confirmed) {
            if (confirmed) {
                var request = $osf.ajaxJSON("DELETE", url, {isCors: true});

                request.done(function () {
                        self.content.destroy(appData);
                        $osf.growl('Deletion', appData.name() + ' has been deleted', 'success');
                    });

                request.fail(function () {
                        $osf.growl('Error', 'Could not delete application. Please refresh the page and try ' +
                                   'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                                   'if the problem persists.', 'danger');
                    });
            }
        }
    })
};


var ApplicationsList = function (selector, urls, modes) {
    this.viewModel = new ApplicationsListViewModel(urls, modes);
    $osf.applyBindings(this.viewModel, selector);
};

var ApplicationDetail = function (selector, urls, modes) {
    this.viewModel = new ApplicationViewModel(urls, modes);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    ApplicationsList: ApplicationsList,
    ApplicationDetail: ApplicationDetail
};
