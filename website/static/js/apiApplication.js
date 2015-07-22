/*
 *  Knockout views for the Developer application pages: List and Create/Edit pages.
 */


'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var historyjs = require('exports?History!history');

var ko = require('knockout');
require('knockout.validation');
require('knockout.punches');
ko.punches.enableAll();
var Raven = require('raven-js');

var koHelpers = require('./koHelpers');  // URL validators etc
var $osf = require('./osfHelpers');
var oop = require('js/oop');


/*
 *  Store the data related to a single API application
 */
var ApplicationData = oop.defclass({
    constructor: function (data) {  // Read in API data and store as object
        data = data || {};

        // User-editable fields
        this.name = ko.observable(data.name)
            .extend({required: true});
        this.description = ko.observable(data.description);
        this.homeUrl = ko.observable(data.home_url)
            .extend({
                url: true,
                ensureHttp: true,
                required: true
            });
        this.callbackUrl = ko.observable(data.callback_url)
            .extend({
                url: true,
                ensureHttp: true,
                required: true
            });

        // Other fields. Owner and client ID should never change within this view.
        this.owner = data.owner;
        this.clientId = data.client_id;
        this.clientSecret = ko.observable(data.client_secret);
        this.webDetailUrl = data.links ? data.links.html : undefined;
        this.apiDetailUrl = data.links ? data.links.self : undefined;

        // Enable value validation in form
        this.validated =  ko.validatedObservable(this);

        this.isValid = ko.computed(function () {
            return this.validated.isValid();
        }.bind(this));
    },

    serialize: function () {
        return { // Convert data to JSON-serializable format consistent with API
            name: this.name(),
            description: this.description(),
            home_url: this.homeUrl(),
            callback_url: this.callbackUrl(),
            client_id: this.clientId,
            client_secret: this.clientSecret(),
            owner: this.owner
        };
    }
});

/*
 * Fetch data about applications
 */
var ApplicationDataClient = oop.defclass({
    /*
     * Create the client for server operations on ApplicationData objects.
     * @param {Object} apiListUrl: The api URL for application listing/creation
     */
    constructor: function (apiListUrl) {
        this.apiListUrl = apiListUrl;
    },
    _fetchData: function (url) {
        var ret = $.Deferred();
        var request = $osf.ajaxJSON('GET', url, {isCors: true});

        request.done(function (data) {
            ret.resolve(this.unserialize(data));
        }.bind(this));

        request.fail(function (xhr, status, error) {
            ret.reject(xhr, status, error);
        }.bind(this));

        return ret.promise();
    },
    fetchList: function () {
        return this._fetchData(this.apiListUrl);
    },
    fetchOne: function (url) {
        return this._fetchData(url);
    },
    _sendData: function (appData, url, method) {
        var ret = $.Deferred();

        var payload = appData.serialize();
        var request = $osf.ajaxJSON(method, url, {isCors: true, data: payload});

        request.done(function (data) { // The server response will contain the newly created/updated record
            ret.resolve(new ApplicationData(data.data));
        }.bind(this));
        request.fail(function (xhr, status, error) {
            ret.reject(xhr, status, error);
        });
        return ret.promise();
    },
    createOne: function (appData) {
        var url = this.apiListUrl;
        return this._sendData(appData, url, 'POST');
    },
    updateOne: function (appData) {
        var url = appData.apiDetailUrl;
        return this._sendData(appData, url, 'PATCH');
    },
    deleteOne: function (appData) {
        var url = appData.apiDetailUrl;
        return $osf.ajaxJSON('DELETE', url, {isCors: true});
    },
    unserialize: function (apiData) {
        var result;
        // Check return type: return one object (detail view) or list of objects (list view) as appropriate.
        if (Array.isArray(apiData.data)) {
            result = $.map(apiData.data, function (item) {
                return new ApplicationData(item);
            });
        } else if (apiData.data) {
            result = new ApplicationData(apiData.data);
        } else {
            result = null;
        }
        return result;
    }
});

/*
  ViewModel for List views
 */
var ApplicationsListViewModel = oop.defclass({
    constructor: function (urls) {
        this.urls = urls;
        // Set up data storage
        this.appData = ko.observableArray();
        this.sortByName = ko.computed(function () {
            return this.appData().sort(function (a,b) {
                var an = a.name().toLowerCase();
                var bn = b.name().toLowerCase();
                return an === bn ? 0 : (an < bn ? -1 : 1);
            });
        }.bind(this));

        // Set up data access client
        this.client = new ApplicationDataClient(urls.apiListUrl);
    },
    init: function () {
        var request = this.client.fetchList();
        request.done(function (data) {
            this.appData(data);
        }.bind(this));

        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                'Data not loaded. Please refresh the page and try ' +
                'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                'if the problem persists.',
                'danger');

            Raven.captureMessage('Error fetching list of registered applications', {
                url: this.urls.apiListUrl,
                status: status,
                error: error
            });
        }.bind(this));
    },
    deleteApplication: function (appData) {
        bootbox.confirm({
            title: 'De-register application?',
            message: 'Are you sure you want to de-register this application and revoke all access tokens? This cannot be reversed.',
            callback: function (confirmed) {
                if (confirmed) {
                    var request = this.client.deleteOne(appData);
                    request.done(function () {
                            this.appData.destroy(appData);
                            $osf.growl('Deletion', '"' + appData.name() + '" has been deleted', 'success');
                    }.bind(this));
                    request.fail(function () {
                            $osf.growl('Error',
                                        'Could not delete application. Please refresh the page and try ' +
                                          'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                                          'if the problem persists.',
                                        'danger');
                    }.bind(this));
                }
            }.bind(this)
        });
    }
});


/*
  ViewModel for Detail views (create and update pages- related though distinct behaviors in a single ViewModel)
    Expects a urls object containing webListUrl, apiListUrl, and apiDetailUrl values. If apiDetailUrl is blank, it
    behaves like a create view.
 */
var ApplicationDetailViewModel = oop.defclass({
    constructor: function (urls) {
        this.appData = ko.observable();
        // Set up data access client
        this.urls = urls;

        this.client = new ApplicationDataClient(urls.apiListUrl);

        // Control success/failure messages above submit buttons
        this.showMessages = ko.observable(false);
        this.message = ko.observable();
        this.messageClass = ko.observable();

        // // If no detail url provided, render view as though it was a creation form. Otherwise, treat as READ/UPDATE.
        this.apiDetailUrl = ko.observable(urls.apiDetailUrl);
        this.isCreateView = ko.computed(function () {
            return !this.apiDetailUrl();
        }.bind(this));
    },
    init: function () {
        if (this.isCreateView()) {
            this.appData(new ApplicationData());
        } else {
            var request = this.client.fetchOne(this.apiDetailUrl());
            request.done(function (data) {
                this.appData(data);
            }.bind(this));
            request.fail(function(xhr, status, error) {
                $osf.growl('Error',
                             'Data not loaded. Please refresh the page and try ' +
                              'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                              'if the problem persists.',
                            'danger');

                Raven.captureMessage('Error fetching application data', {
                    url: this.apiDetailUrl(),
                    status: status,
                    error: error
                });
            }.bind(this));
        }
    },
    updateApplication: function () {
        if (!this.appData().isValid()) {
            this.showMessages(true);
            return;
        }
        var request = this.client.updateOne(this.appData());
        request.done(function (data) {
            this.appData(data);
            this.changeMessage(
            'Application data updated',
            'text-success',
            5000);
        }.bind(this));

        request.fail(function (xhr, status, error) {
            $osf.growl('Error',
                       'Failed to update data. Please refresh the page and try ' +
                         'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                         'if the problem persists.',
                       'danger');

            Raven.captureMessage('Error updating instance', {
                url: this.apiDetailUrl,
                status: status,
                error: error
            });
        }.bind(this));
    },
    createApplication: function () {
        if (!this.appData().isValid()) {
            this.showMessages(true);
            return;
        }
        var request = this.client.createOne(this.appData());
        request.done(function (data) {
            this.appData(data);
            this.changeMessage('Successfully registered new application', 'text-success', 5000);
            this.apiDetailUrl(data.apiDetailUrl); // Toggle ViewModel --> act like a display view now.
            historyjs.replaceState({}, '', data.webDetailUrl);  // Update address bar to show new detail page
        }.bind(this));

        request.fail(function (xhr, status, error) {
            $osf.growl('Error',
                       'Failed to send data. Please refresh the page and try ' +
                         'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                         'if the problem persists.',
                       'danger');

            Raven.captureMessage('Error registering new OAuth2 application', {
                url: this.apiDetailUrl,
                status: status,
                error: error
            });
        }.bind(this));
    },
    cancelChange: function () {
        // TODO: Add change tracking features a la profile page JS
        window.location = this.urls.webListUrl;
    },
    changeMessage: function (text, css, timeout) {
        // Display messages near save button. Overlaps with profile.js.
    this.message(text);
    var cssClass = css || 'text-info';
    this.messageClass(cssClass);
    if (timeout) {
        // Reset message after timeout period
        setTimeout(function () {
                this.message('');
                this.messageClass('text-info');
            }.bind(this),
            timeout
        );
    }}
});


var ApplicationsList = function (selector, urls) {
    this.viewModel = new ApplicationsListViewModel(urls);
    $osf.applyBindings(this.viewModel, selector);
    this.viewModel.init();
};

var ApplicationDetail = function (selector, urls) {
    this.viewModel = new ApplicationDetailViewModel(urls);
    $osf.applyBindings(this.viewModel, selector);
    this.viewModel.init();
};

module.exports = {
    ApplicationsList: ApplicationsList,
    ApplicationDetail: ApplicationDetail
};
