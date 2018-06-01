'use strict';

var $ = require('jquery');
var ko = require('knockout');

var WhitelistPreprintProvidersViewModel = function() {
    var self = this;
    self.preprintProviders = ko.observableArray([]);
    self.providersAdded = ko.observableArray([]);
    self.providersRemoved = ko.observableArray([]);
    self.providersWhitelisted = ko.observableArray([]);
    self.shareApiUrl = window.templateVars.shareApiUrl + "/api/v2/search/creativeworks/_search";
    self.apiV2Url = window.templateVars.apiV2Url + "preprint_providers/";
    self.isDetailPage = ko.observable(true);
    self.linkText = ko.observable("Add providers");
    self.pageTitle = ko.observable("Whitelist of SHARE Preprint Providers");
    self.isLoading = ko.observable(true);
};

WhitelistPreprintProvidersViewModel.prototype.updatePreprintProviders = function() {
    var self = this;
    var queryObj = {
        "size": 0,
        "query": {"terms": {"types": ["preprint"]}},
        "aggregations": {"sources": {"terms": {"field": "sources", "size": 500}}}
    };

    var shareApiCall =  $.ajax({
        url: self.shareApiUrl,
        type: "POST",
        dataType: "json",
        contentType: "application/json",
        data: JSON.stringify(queryObj)
    });

    var apiV2Call =  $.get(self.apiV2Url);

    $.when(shareApiCall, apiV2Call).then(function (firstResponse, secondResponse) {
        var shareProviders = firstResponse[0].aggregations.sources.buckets.map(function(item) {
            return item.key;
        }).filter(function (item) {
            return secondResponse[0].meta.whitelisted_providers.indexOf(item) < 0;
        });

        var internalProviders = secondResponse[0].data.map(function(item) {
            return item.attributes.name;
        });

        var externalProviders = shareProviders.filter( function( item ) {
            return internalProviders.indexOf( item ) < 0;
        });

        externalProviders.forEach(function(item){
            self.preprintProviders.push({
                "name": item
            });
        });
        self.isLoading(false);
    });
};

WhitelistPreprintProvidersViewModel.prototype.preprintProviderDetail = function() {
    var self = this;
    var apiV2Call = $.get(self.apiV2Url);
    apiV2Call.then(function(response){
        var providersWhitelisted = response.meta.whitelisted_providers;
        providersWhitelisted.forEach(function(item) {
            self.providersWhitelisted.push({
                "name": item,
            });
        });
        self.isLoading(false);
    });
};

WhitelistPreprintProvidersViewModel.prototype.switchPage = function() {
    var self = this;
    self.preprintProviders([]);
    self.providersAdded([]);
    self.providersWhitelisted([]);
    self.isLoading(true);
    if (self.isDetailPage()) {
        self.isDetailPage(false);
        self.linkText("Delete providers");
        self.pageTitle('Add Preprint Providers to Whitelist');
        self.updatePreprintProviders();
    } else {
        self.isDetailPage(true);
        self.linkText("Add providers");
        self.pageTitle("Whitelist of SHARE Preprint Providers");
        self.preprintProviderDetail();
    }
};

WhitelistPreprintProvidersViewModel.prototype.submit = function() {
    var self = this;
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
    if (self.isDetailPage()){
        var deleteCall =  $.ajax({
            url: window.location.pathname,
            type: "DELETE",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                removed: this.providersRemoved()
            })
        });
        deleteCall.then(window.location.reload());
    } else {
        var addCall =  $.ajax({
            url: window.location.pathname,
            type: "POST",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                added: this.providersAdded()
            })
        });
        addCall.then(window.location.reload());
    }
};

$(document).ready(function() {
    var viewModel = new WhitelistPreprintProvidersViewModel();
    ko.applyBindings(viewModel);
    viewModel.preprintProviderDetail();
});
