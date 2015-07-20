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

        // Other fields
        this.clientId = data.client_id;
        this.clientSecret = ko.observable(data.client_secret);

        this.webDetailUrl = data.links.html; // TODO: Rename detailUrl to webDetailUrl and update usages
        this.apiDetailUrl = data.links.self;  // TODO: Rename apiUrl to apiDetailUrl and update usages
    },

    serialize: function () {
        return {
            name: this.name(),
            description: this.description(),
            home_url: this.homeUrl(),
            callback_url: this.callbackUrl(),
            client_id: this.clientId,
            client_secret: this.clientSecret(),
            owner: this.owner()
        }
    },
    // Enable value validation in form
    validated: ko.validatedObservable(this)

    //// TODO: Fix?
    //isValid: ko.computed(function () {
    //    return this.validated.isValid();
    //})
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

        request.fail(function (xhr, status, error) {
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
            ret.reject(xhr, status, error);
        }.bind(this));

        return ret.promise();
    },
    fetchList: function () {
        return this._fetchData(this.urls.listUrl);
    },
    fetchOne: function () {
        return this._fetchData(this.urls.detailUrl);
    },
    createOne: function () {
        var ret = $.Deferred();

        var request = $osf.ajaxJSON('POST', url, {isCors: true, data: payload});

        request.done(function (data) {
            ret.resolve(new ApplicationData(data));
            window.location = data.data.links.html; // Update address bar to show new detail page TODO: Move to view code to separate from client
        }.bind(this));

        request.fail(function (xhr, status, err) {
            $osf.growl('Error', 'Could not send request. Please refresh the page and try ' +
            'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
            'if the problem persists.', 'danger');

            Raven.captureMessage('Error updating instance', {
                url: url,
                status: status,
                error: err
            });
            ret.reject(xhr, status. error);
        });
        return ret.promise();
    },
    updateOne: function () {
        var ret = $.Deferred();
        // TODO: Implement
        return ret.promise();
    },
    deleteOne: function (url) {
        //var ret = $.Deferred();
        // TODO: Passing promise unmodified
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
        this.urls = urls;
        this.client = new ApplicationDataClient(urls);
    },
    init: function () {
        this.client.fetchList().done(function (data) {
            console.log("List Data fetched", data);
            this.appData(data);
        }.bind(this))
    },
    deleteApplication: function (appData) {
        bootbox.confirm({
            title: 'De-register application?',
            message: 'Are you sure you want to de-register this application and revoke all access tokens? This cannot be reversed.',
            callback: function (confirmed) {
                if (confirmed) {
                    var promise = this.client.deleteApplication(url);
                    request.done(function () {
                            this.appData.destroy(appData);
                            $osf.growl('Deletion', '"' + appData.name() + '" has been deleted', 'success')
                    }.bind(this));
                    request.fail(function () {
                            $osf.growl('Error', 'Could not delete application. Please refresh the page and try ' +
                                       'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                                       'if the problem persists.', 'danger')
                    }.bind(this));
                }
            }
        });
    }
});


/*
  ViewModel for Detail views
 */
// TODO: Implement









var applicationFetch = function (url) { // Function shared by list and detail ViewModels
    var self = this;
    var request = $osf.ajaxJSON('GET', url, {isCors: true});

    request.done(function (data) {
        var result;
        // Check return type to handle both list and detail views
        if (Array.isArray(data.data)) {  // ES5 dependent
            result = $.map(data.data, function (item) {
                return new ApplicationData(item);
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
        });
    });
};


/*
 * Create (or update) the data for a single application. On creation, page seamlessly transitions to acting
 * like an update page.
 */
var ApplicationViewModel = function (urls) {
    // Read and update operations

    var self = this;
    self.content = ko.observable(new ApplicationData());
    self.message = ko.observable();
    self.messageClass = ko.observable();

    self.showMessages = ko.observable(false);

    self.dataUrl = urls.dataUrl; // Use for editing existing instances
    self.submitUrl = urls.submitUrl; // Use for creating new instances
    self.listPageUrl = urls.listPageUrl;

    if (self.dataUrl){ // Support detail views
        self.fetch(self.dataUrl);
    }
};

ApplicationViewModel.prototype.fetch = applicationFetch;

ApplicationViewModel.prototype.updateApplication = function () {
    // Update an existing application (has a known dataUrl) via PATCH request
    var self = this;

    if (!self.content().isValid()){
        self.showMessages(true);
        return;
    }

    var url = self.dataUrl;

    var payload = self.content().serialize();

    var request = $osf.ajaxJSON('PATCH', url, {isCors: true, data: payload});

    request.done(function (data) {
        self.content().deserialize(data.data);  // Update the data with what request returns- reflect server side cleaning
        self.changeMessage(
            'Application data submitted',  // TODO: Some pages (eg profile) show a one-line message for updates; others use a growl box. Current best practices?
            'text-success',
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

    if (!self.content().isValid()){
        self.showMessages(true);
        return;
    }

    var payload = self.content().serialize();

    var url = self.submitUrl;

    var request = $osf.ajaxJSON('POST', url, {isCors: true, data: payload});

    request.done(function (data) {
        self.content().deserialize(data.data);  // Update the data with what request returns- reflect server side cleaning

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

ApplicationViewModel.prototype.cancelChange = function(){
    // TODO: Add change tracking features/ confirm to exit dialog a la profile.js (hinging on refactoring profile.js behaviors into common base file that works with apiv2 return vals)

    // FIXME: self.listPageUrl is undefined, but shouldn't be (it's recognized in constructor)
    window.location = self.listPageUrl;
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

var ApplicationsList = function (selector, urls) {
    this.viewModel = new ApplicationsListViewModel(urls);
    $osf.applyBindings(this.viewModel, selector);
    this.viewModel.init();
};

var ApplicationDetail = function (selector, urls, modes) {
    this.viewModel = new ApplicationViewModel(urls, modes);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    ApplicationsList: ApplicationsList,
    ApplicationDetail: ApplicationDetail
};
