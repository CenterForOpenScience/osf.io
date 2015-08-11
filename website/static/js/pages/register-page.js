'use strict';
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');

var language = require('js/osfLanguage').registrations;
var registrationUtils = require('js/registrationUtils');
var registrationEmbargo = require('js/registrationEmbargo');

var ctx = window.contextVars;

require('pikaday-css');

$(document).ready(function() {
    // if registering draft
    if (ctx.draft) {
        var ViewModel = function() {
            var self = this;

            self.embargoAddon = new registrationEmbargo.ViewModel();
            self.draft = new registrationUtils.Draft(ctx.draft);

            self.focusOnPicker = ko.observable(false);

            self.continueText = ko.observable('');
            self.canSubmit = ko.computed(function() {
                return /^\s*register\s*$/gi.test(self.continueText());
            });
        };
        ViewModel.prototype.registerDraft = function() {
            var self = this;

            // If embargo is requested, verify its end date, and inform user if date is out of range
            if (self.embargoAddon.requestingEmbargo()) {
                if (!self.embargoAddon.isEmbargoEndDateValid()) {
                    self.continueText('');
                    $osf.growl(
                        language.invalidEmbargoTitle,
                        language.invalidEmbargoMessage,
                        'warning'
                    );
                    self.focusOnPicker(true);
                }
            }
            self.draft.beforeRegister({
                registrationChoice: self.embargoAddon.registrationChoice(),
                embargoEndDate: self.embargoAddon.embargoEndDate().toUTCString()
            });
        };

        var viewModel = new ViewModel();
        // Apply view model
        $osf.applyBindings(viewModel, '#draftRegistrationScope');
    } 
    // if viewing registered metadata
    else {
        var metaSchema = new registrationUtils.MetaSchema(ctx.node.registrationMetaSchema);

        var metaDataViewModel = {
            metaSchema: metaSchema,
            schemaData: ctx.node.registrationMetaData
        };
        $osf.applyBindings(metaDataViewModel, '#registrationMetaDataScope');
    }
});
