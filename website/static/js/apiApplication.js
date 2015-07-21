/*
 *  Knockout views for the Developer application pages: List and Create/Edit pages.
 */


'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
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
    constructor: function (data) {
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
        }.bind(this))
    },

    serialize: function () {
        return {
            name: this.name(),
            description: this.description(),
            home_url: this.homeUrl(),
            callback_url: this.callbackUrl(),
            client_id: this.clientId,
            client_secret: this.clientSecret(),
            owner: this.owner
        }
    }
});

/*
 * Fetch data about applications
 */
var ApplicationDataClient = oop.defclass({
    /*
     * Create the client.
     * @param {Object} urls: An object with urls for operations. Expects fields listUrl and detailUrl.
     */
    constructor: function (urls) {
        this.urls = urls || {};
    },
    _fetchData: function (url) {
        var ret = $.Deferred();
        var request = $osf.ajaxJSON('GET', url, {isCors: true});

        request.done(function (data) {
            ret.resolve(this.unserialize(data));
        }.bind(this));

        request.fail(function (xhr, status, err) {
            $osf.growl('Error',  // TODO: UI in client? (following accountSettings.js but not great pattern)
                         'Data not loaded. Please refresh the page and try ' +
                         'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                         'if the problem persists.',
                       'danger');

            Raven.captureMessage('Error fetching application data', {
                url: url,
                status: status,
                error: err
            });
            ret.reject(xhr, status, err);
        }.bind(this));

        return ret.promise();
    },
    fetchList: function () {
        return this._fetchData(this.urls.apiListUrl);
    },
    fetchOne: function () {
        return this._fetchData(this.urls.apiDetailUrl);
    },
    createOne: function (appData) {
        var ret = $.Deferred();

        var url = this.urls.apiListUrl;
        var payload = appData.serialize();
        var request = $osf.ajaxJSON('POST', url, {isCors: true, data: payload});

        request.done(function (data) {
            ret.resolve(new ApplicationData(data.data));
            // TODO: Display a status message on the page (how to do this when submission is separate from the server?)
        }.bind(this));
        request.fail(function (xhr, status, err) {
            ret.reject(xhr, status, err);
        });
        return ret.promise();
    },
    updateOne: function (appData) {  // TODO: use appData object to get both url and payload from one argument
        var ret = $.Deferred();

        var url = appData.apiDetailUrl;
        var payload = appData.serialize();

        var request = $osf.ajaxJSON('PATCH', url, {isCors: true, data: payload});

        request.done(function(data) {
            ret.resolve(new ApplicationData(data.data));
        }.bind(this));

        request.fail(function (xhr, status, err) {
            ret.reject(xhr. status, err)
        }.bind(this));
        return ret.promise();
    },
    deleteOne: function (appData) {
        var url = appData.apiDetailUrl;
        return $osf.ajaxJSON('DELETE', url, {isCors: true});
    },
    unserialize: function (data) {
        var result;
        // Check return type: return one object (detail view) or list of objects (list view) as appropriate.
        if (Array.isArray(data.data)) {
            result = $.map(data.data, function (item) {
                return new ApplicationData(item);
            });
        } else if (data.data) {
            result = new ApplicationData(data.data);
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
        this.client = new ApplicationDataClient(urls);
    },
    init: function () {
        this.client.fetchList()
            .done(function (data) {
                this.appData(data);
            }.bind(this))
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
                            $osf.growl('Deletion', '"' + appData.name() + '" has been deleted', 'success')
                    }.bind(this));
                    request.fail(function () {
                            $osf.growl('Error',
                                        'Could not delete application. Please refresh the page and try ' +
                                          'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                                          'if the problem persists.',
                                        'danger')
                    }.bind(this));
                }
            }
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

        this.client = new ApplicationDataClient(urls);

        this.showMessages = ko.observable(false);

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
            this.client.fetchOne()
                .done(function (data) {
                    this.appData(data);
                }.bind(this))
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
            // TODO: Add a message that data was submitted successfully- self.changeMessage lines
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
        }.bind(this))
    },
    createApplication: function () {
        // TODO: DRY with update?
        if (!this.appData().isValid()) {
            this.showMessages(true);
            return;
        }
        var request = this.client.createOne(this.appData());
        request.done(function (data) {
            this.appData(data);
            window.location = data.webDetailUrl; // Update address bar to show new detail page TODO: Move to view code to separate from client and use appData to encapsulate link var
            // TODO: Add a message that data was submitted successfully- self.changeMessage lines
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
        }.bind(this))
    },
    cancelChange: function () {
        // TODO: Add change tracking features a la profile page JS
        window.location = this.urls.webListUrl
    }
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
