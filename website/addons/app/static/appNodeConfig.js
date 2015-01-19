require('select2');
var $ = require('jQuery');
require('knockout-punches');
var ko = require('knockout');
var $osf = require('osfHelpers');


// Enable knockout punches
ko.punches.enableAll();

var ViewModel = function(url) {
    var self = this;
    self.url = url;
    // TODO: Initialize observables, computes, etc. here
    self.customRoutes = ko.observableArray([]);
    // Flashed messages
    self.message = ko.observable('');
    self.customUrl = ko.observable('');
    self.customQuery = ko.observable('');

    self.createCustomRoute = function() {
        var route = {
            route: self.customUrl(),
            query: self.customQuery()
        };

        $.ajax({
            url: self.url,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(route),
            success: function() {
                route.url = self.url + route.route + '/';
                self.customRoutes.push(route);
                self.customUrl('');
                self.customQuery('');
            },
            error: function() {
                self.message('Failed to create custom route.');
            }
        });
    };

    // Get data from the config GET endpoint
    function onFetchSuccess(response) {
        // Update view model
        self.customRoutes(ko.utils.arrayMap(Object.keys(response), function(key) {
            return {
                url: response[key],
                query: key
            };
        }));

    }
    function onFetchError(xhr, textstatus, error) {
        self.message('Could not fetch settings.');
    }
    function fetch() {
        $.ajax({url: self.url, type: 'GET', dataType: 'json',
                success: onFetchSuccess,
                error: onFetchError
        });
    }

    fetch();
};

// var AppNodeSettings = function() {
//     $('#sortables').select2({
//         dataCache: [],
//         allowClear: true,
//         placeholder: 'Select a key to sort on by default',
//         query: function(query) {
//             var self = this;
//             if (self.dataCache.length !== 0) {
//                 query.callback({results: self.dataCache});
//             } else {
//                 $.ajax({
//                     url: '',

//                 })
//             }
//         });
// }

function AppNodeConfig(selector, url) {
    // Initialization code
    var self = this;
    self.viewModel = new ViewModel(url);
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = AppNodeConfig;
