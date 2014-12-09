'use strict';
var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var $osf = require('osf-helpers');

ko.punches.enableAll();
var language = require('osf-language').Addons.dataverse;

function ViewModel(url) {
    var self = this;
    self.connected = ko.observable();
    self.dataverse = ko.observable();
    self.dataverseUrl = ko.observable();
    self.study = ko.observable();
    self.doi = ko.observable();
    self.studyUrl = ko.observable('');
    self.citation = ko.observable('');
    self.loaded = ko.observable(false);

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info')

    self.init = function() {
        $.ajax({
            url: url, type: 'GET', dataType: 'json',
            success: function(response) {
                var data = response.data;
                self.connected(data.connected);
                self.dataverse(data.dataverse);
                self.dataverseUrl(data.dataverseUrl);
                self.study(data.study);
                self.doi(data.doi);
                self.studyUrl(data.studyUrl);
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
