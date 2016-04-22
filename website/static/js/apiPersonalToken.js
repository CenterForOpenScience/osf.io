/*
 *  Knockout views for the Personal Access Token pages: List and Create/Edit pages.
 */


'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var historyjs = require('exports?History!history');
var moment = require('moment');

var ko = require('knockout');
require('knockout.validation');
var Raven = require('raven-js');

var ChangeMessageMixin = require('js/changeMessage');
var koHelpers = require('./koHelpers');  // URL validators etc
var $osf = require('./osfHelpers');
var oop = require('js/oop');
var language = require('js/osfLanguage');
var makeClient = require('js/clipboard');


/*
 *  Store the data related to a single API Personal Token
 */
var TokenData = oop.defclass({
    constructor: function (data) {  // Read in API data and store as object
        data = data || {};
        var attributes = data.attributes || {};

        // User-editable fields
        this.name = ko.observable(attributes.name)
            .extend({required: true, maxLength:200});

        this.scopes = ko.observableArray(attributes.scopes ? attributes.scopes.split(' ') : undefined)
            .extend({required: true});

        this.token_id = ko.observable(attributes.token_id);

        // Other fields. Owner and ID should never change within this view.
        this.id = data.id;

        this.owner = attributes.user_id;
        this.webDetailUrl = data.links ? data.links.html : undefined;
        this.apiDetailUrl = data.links ? data.links.self : undefined;

        // Enable value validation in form
        this.validated =  ko.validatedObservable(this);

        this.isValid = ko.computed(function () {
            return this.validated.isValid();
        }.bind(this));
    },

    serialize: function () {
        return { // Convert data to JSON-serializable format consistent with JSON API v1.0 spec
            data: {
                id: this.id,
                type: 'tokens',
                attributes: {
                    name: this.name(),
                    scopes: this.scopes().toString().replace(/,/g, ' ') || '',
                    user_id: this.owner
                }
            }
        };
    }
});

/*
 * Fetch data about tokens
 */
var TokenDataClient = oop.defclass({
    /*
     * Create the client for server operations on TokenData objects.
     * @param {Object} apiListUrl: The api URL for token listing/creation
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
    _sendData: function (tokenData, url, method) {
        var ret = $.Deferred();

        var payload = tokenData.serialize();
        var request = $osf.ajaxJSON(method, url, {isCors: true, data: payload});

        request.done(function (data) { // The server response will contain the newly created/updated record
            ret.resolve(this.unserialize(data));
        }.bind(this));
        request.fail(function (xhr, status, error) {
            ret.reject(xhr, status, error);
        });
        return ret.promise();
    },
    createOne: function (tokenData) {
        var url = this.apiListUrl;
        return this._sendData(tokenData, url, 'POST');
    },
    updateOne: function (tokenData) {
        var url = tokenData.apiDetailUrl;
        return this._sendData(tokenData, url, 'PATCH');
    },
    deleteOne: function (tokenData) {
        var url = tokenData.apiDetailUrl;
        return $osf.ajaxJSON('DELETE', url, {isCors: true});
    },
    unserialize: function (apiData) {
        var result;
        // Check return type: return one object (detail view) or list of objects (list view) as appropriate.
        if (Array.isArray(apiData.data)) {
            result = $.map(apiData.data, function (item) {
                return new TokenData(item);
            });
        } else if (apiData.data) {
            result = new TokenData(apiData.data);
        } else {
            result = null;
        }
        return result;
    }
});

/*
  ViewModel for List views
 */
var TokensListViewModel = oop.defclass({
    constructor: function (urls) {
        this.apiListUrl = urls.apiListUrl;
        this.webCreateUrl = urls.webCreateUrl;
        // Set up data storage
        this.tokenData = ko.observableArray();
        this.sortedByName = ko.pureComputed(function () {
            return this.tokenData().sort(function (a,b) {
                var an = a.name().toLowerCase();
                var bn = b.name().toLowerCase();
                return an === bn ? 0 : (an < bn ? -1 : 1);
            });
        }.bind(this));

        // Set up data access client
        this.client = new TokenDataClient(this.apiListUrl);
    },
    init: function () {
        var request = this.client.fetchList();
        request.done(function (data) {
            this.tokenData(data);
        }.bind(this));

        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                language.apiOauth2Token.dataListFetchError,
                'danger');

            Raven.captureMessage('Error fetching list of registered personal access tokens', {
                extra: {
                    url: this.apiListUrl,
                    status: status,
                    error: error
                }
            });
        }.bind(this));
    },
    deleteToken: function (tokenData) {
        bootbox.confirm({
            title: 'Deactivate personal access token?',
            message: language.apiOauth2Token.deactivateConfirm,
            callback: function (confirmed) {
                if (confirmed) {
                    var request = this.client.deleteOne(tokenData);
                    request.done(function () {
                            this.tokenData.destroy(tokenData);
                            var tokenName = $osf.htmlEscape(tokenData.name());
                            $osf.growl('Deletion', '"' + tokenName + '" has been deactivated', 'success');
                    }.bind(this));
                    request.fail(function () {
                            $osf.growl('Error',
                                       language.apiOauth2Token.deactivateError,
                                       'danger');
                    }.bind(this));
                }
            }.bind(this),
            buttons:{
                confirm:{
                    label:'Deactivate',
                    className:'btn-danger'
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
var TokenDetailViewModel = oop.extend(ChangeMessageMixin, {
    constructor: function (urls) {
        this.super.constructor.call(this);
        var placeholder = new TokenData();
        this.tokenData = ko.observable(placeholder);

        // Track whether data has changed, and whether user is allowed to leave page anyway
        this.originalValues = ko.observable(placeholder.serialize());
        this.dirty = ko.computed(function(){
            return JSON.stringify(this.originalValues()) !== JSON.stringify(this.tokenData().serialize());
        }.bind(this));
        this.allowExit = ko.observable(false);

        // Set up data access client
        this.webListUrl = urls.webListUrl;
        this.client = new TokenDataClient(urls.apiListUrl);

        // Toggle hiding token id (in detail view)
        this.showToken = ko.observable(false);
        // Toggle display of validation messages
        this.showMessages = ko.observable(false);

        // // If no detail url provided, render view as though it was a creation form. Otherwise, treat as READ/UPDATE.
        this.apiDetailUrl = ko.observable(urls.apiDetailUrl);
        this.isCreateView = ko.computed(function () {
            return !this.apiDetailUrl();
        }.bind(this));
    },
    init: function () {
        if (!this.isCreateView()) {
            // Add listener to prevent user from leaving page if there are unsaved changes
            $(window).on('beforeunload', function () {
                if (this.dirty() && !this.allowExit()) {
                    return 'There are unsaved changes on this page.';
                }
            }.bind(this));

            var request = this.client.fetchOne(this.apiDetailUrl());
            request.done(function (dataObj) {
                this.tokenData(dataObj);
                this.originalValues(dataObj.serialize());
            }.bind(this));
            request.fail(function(xhr, status, error) {
                $osf.growl('Error',
                             language.apiOauth2Token.dataFetchError,
                            'danger');

                Raven.captureMessage('Error fetching token data', {
                    extra: {
                        url: this.apiDetailUrl(),
                        status: status,
                        error: error
                    }
                });
            }.bind(this));
        }
    },
    updateToken: function () {
        if (!this.dirty()){
            // No data needs to be sent to the server, but give the illusion that form was submitted
            this.changeMessage(
                language.apiOauth2Token.dataUpdated,
                'text-success',
                5000);
            return;
        }

        var request = this.client.updateOne(this.tokenData());
        request.done(function (dataObj) {
            this.tokenData(dataObj);
            this.originalValues(dataObj.serialize());
            this.changeMessage(
                language.apiOauth2Token.dataUpdated,
                'text-success',
                5000);
        }.bind(this));

        request.fail(function (xhr, status, error) {
            $osf.growl('Error',
                       language.apiOauth2Token.dataSendError,
                       'danger');

            Raven.captureMessage('Error updating instance', {
                extra: {
                    url: this.apiDetailUrl,
                    status: status,
                    error: error
                }
            });
        }.bind(this));
        return request;
    },
    createToken: function () {
        var request = this.client.createOne(this.tokenData());
        request.done(function (dataObj) {
            this.tokenData(dataObj);
            this.originalValues(dataObj.serialize());
            this.showToken(true);
            makeClient(document.getElementById('copy-button'));
            this.changeMessage(language.apiOauth2Token.creationSuccess, 'text-success');
            this.apiDetailUrl(dataObj.apiDetailUrl); // Toggle ViewModel --> act like a display view now.
            historyjs.replaceState({}, '', dataObj.webDetailUrl);  // Update address bar to show new detail page
        }.bind(this));

        request.fail(function (xhr, status, error) {
            $osf.growl('Error',
                       language.apiOauth2Token.dataSendError,
                       'danger');

            Raven.captureMessage('Error registering new OAuth2 personal access token', {
                extra: {
                    url: this.apiDetailUrl,
                    status: status,
                    error: error
                }
            });
        }.bind(this));
    },
    submit: function () {
        // Validate and dispatch form to correct handler based on view type
        if (!this.tokenData().isValid()) {
            // Turn on display of validation messages
            this.showMessages(true);
        } else {
            this.showMessages(false);
            if (this.isCreateView()) {
                this.createToken();
            } else {
                this.updateToken();
            }
        }
    },
    deleteToken: function () {
        var tokenData = this.tokenData();
        bootbox.confirm({
            title: 'Deactivate token?',
            message: language.apiOauth2Token.deactivateConfirm,
            callback: function (confirmed) {
                if (confirmed) {
                    var request = this.client.deleteOne(tokenData );
                    request.done(function () {
                        this.allowExit(true);
                        // Don't let user go back to a deleted token page
                        historyjs.replaceState({}, '', this.webListUrl);
                        this.visitList();
                    }.bind(this));
                    request.fail(function () {
                            $osf.growl('Error',
                                       language.apiOauth2Token.deactivateError,
                                       'danger');
                    }.bind(this));
                }
            }.bind(this),
            buttons:{
                confirm:{
                    label:'Deactivate',
                    className:'btn-danger'
                }
            }
        });
    },
    visitList: function () {
        window.location = this.webListUrl;
    },
    cancelChange: function () {
        if (!this.dirty()) {
            this.visitList();
        } else {
            bootbox.confirm({
                title: 'Discard changes?',
                message: language.apiOauth2Token.discardUnchanged,
                callback: function(confirmed) {
                    if (confirmed) {
                        this.allowExit(true);
                        this.visitList();
                    }
                }.bind(this),
                buttons: {
                    confirm: {
                        label:'Discard',
                        className:'btn-danger'
                    }
                }
            });
        }
    },
});


var TokensList = function (selector, urls) {
    this.viewModel = new TokensListViewModel(urls);
    $osf.applyBindings(this.viewModel, selector);
    this.viewModel.init();
};

var TokenDetail = function (selector, urls) {
    this.viewModel = new TokenDetailViewModel(urls);
    $osf.applyBindings(this.viewModel, selector);
    this.viewModel.init();
};

module.exports = {
    TokensList: TokensList,
    TokenDetail: TokenDetail,
    // Make internals accessible directly for testing
    _TokenData: TokenData,
    _TokenDataClient: TokenDataClient,
    _TokensListViewModel: TokensListViewModel,
    _TokenDetailViewModel: TokenDetailViewModel
};
