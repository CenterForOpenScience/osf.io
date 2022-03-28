var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');

var language = require('js/osfLanguage').Addons.metadata;
var osfHelpers = require('js/osfHelpers');
var ChangeMessageMixin = require('js/changeMessage');


var METADATA_URL = '/api/v1/settings/metadata/erad';


function ViewModel() {
    var self = this;

    self.properName = 'Metadata Registries';

    self.eRadResearcherNumber = ko.observable();
    self.lastERadResearcherNumber = ko.observable();
    self.eRadResearcherNumberChanged = ko.pureComputed(function() {
        return self.eRadResearcherNumber() != self.lastERadResearcherNumber();
    }, self);

    ChangeMessageMixin.call(self);

    self.save = function() {
        return $.ajax({
            url: METADATA_URL,
            type: 'PUT',
            data: JSON.stringify({
                researcher_number: self.eRadResearcherNumber()
            }),
            contentType: 'application/json',
            dataType: 'json'
        }).done(function (data) {
            var attrs = (data.data || {}).attributes || {}
            self.eRadResearcherNumber(attrs.researcher_number);
            self.lastERadResearcherNumber(attrs.researcher_number);
        }).fail(function(xhr, status, error) {
            self.changeMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Error while updating addon account', {
                extra: {
                    url: METADATA_URL,
                    status: status,
                    error: error
                }
            });
        });
    };

    self.update = function() {
        return $.ajax({
            url: METADATA_URL,
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
            var attrs = (data.data || {}).attributes || {}
            self.eRadResearcherNumber(attrs.researcher_number);
            self.lastERadResearcherNumber(attrs.researcher_number);
        }).fail(function(xhr, status, error) {
            self.changeMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Error while updating addon account', {
                extra: {
                    url: METADATA_URL,
                    status: status,
                    error: error
                }
            });
        });
    };

    self.update();
}

$.extend(ViewModel.prototype, ChangeMessageMixin.prototype);

function configureUserConfig(selector) {
    var viewModel = new ViewModel();
    osfHelpers.applyBindings(viewModel, selector);
}

configureUserConfig('#metadataScope');
