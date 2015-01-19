var $ = require('jquery');

require('select2');

require('knockout-punches');
var ko = require('knockout');
var $osf = require('osfHelpers');


// Enable knockout punches
ko.punches.enableAll();

var ViewModel = function(url, mappingUrl) {
    var self = this;
    self.url = url;
    self.mappingUrl = mappingUrl;
    // TODO: Initialize observables, computes, etc. here
    self.customRoutes = ko.observableArray([]);
    // Flashed messages
    self.message = ko.observable('');
    self.customUrl = ko.observable('');
    self.customQuery = ko.observable('');
    self.isSortable = ko.observable(false);

    self.setDefaultSearch = function() {
        var request = $osf.postJSON(self.mappingUrl, {
            key: $('#sorts').select2('val')
        });
        //TODO Callback
    };

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
                query: key,
                placeholder: "Select an option"
            };
        }));

    }

    function onKeyFetchSuccess(response) {
        keys = response.keys.map(function(key) {
            return {text: key, id: key};
        });

        if (keys.length > 0) {
            $('#sorts').select2({
                placeholder: 'Select a key to sort on by default',
                allowClear: true,
                width: '75%',
                data: keys
            });

            if (response.selected !== null) {
                $('#sorts').select2('val', response.selected);
            }

            self.isSortable(true);
        }
    }

    function onFetchError(xhr, textstatus, error) {
        self.message('Could not fetch settings.');
    }

    function fetch() {
        $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json',
        }).then(onFetchSuccess, onFetchError);

        //Fetch keys
        $.ajax({
            url: self.mappingUrl,
            type: 'GET',
            dataType: 'json',
        }).then(onKeyFetchSuccess, onFetchError);
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

function AppNodeConfig(selector, url, mappingUrl) {
    // Initialization code
    var self = this;
    self.viewModel = new ViewModel(url, mappingUrl);
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = AppNodeConfig;
