'use strict';
var ko = require('knockout');
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var language = require('js/osfLanguage').Addons.dataverse;

function ViewModel(url) {
    var self = this;
    self.connected = ko.observable();
    self.dataverse = ko.observable();
    self.dataverseUrl = ko.observable();
    self.dataset = ko.observable();
    self.doi = ko.observable();
    self.datasetUrl = ko.observable('');
    self.citation = ko.observable('');
    self.loaded = ko.observable(false);

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    self.init = function() {
        $.ajax({
            url: url, type: 'GET', dataType: 'json',
            success: function(response) {
                var data = response.data;
                self.connected(data.connected);
                self.dataverse(data.dataverse);
                self.dataverseUrl(data.dataverseUrl);
                self.dataset(data.dataset);
                self.doi(data.doi);
                self.datasetUrl(data.datasetUrl);
                self.citation(data.citation);
                self.loaded(true);
            },
            error: function(xhr) {
                self.loaded(true);
                var errorMessage = (xhr.status === 403) ? language.widgetInvalid : language.widgetError;
                self.changeMessage(errorMessage, 'text-danger');
            }
        });
    };

    /** Change the flashed status message */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    };
}

// Public API
function DataverseWidget(selector, url) {
    var self = this;
    self.viewModel = new ViewModel(url);
    $osf.applyBindings(self.viewModel, selector);
    self.viewModel.init();
}

module.exports = DataverseWidget;
