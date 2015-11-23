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

$(function() {
    // opt into tooltip
    $('[data-toggle="tooltip"]').tooltip();

    // if registering draft
    if (ctx.draft) {
        var ViewModel = function() {
            var self = this;

            self.embargoAddon = new registrationEmbargo.ViewModel();
            self.draft = new registrationUtils.Draft(ctx.draft);

            self.focusOnPicker = ko.observable(false);

            self.continueText = ko.observable('');
            self.canSubmit = ko.pureComputed(function() {
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
        ViewModel.prototype.submitForReview = function() {
            var self = this;

            var draft = self.draft;
            var metaSchema = draft.metaSchema;
            var messages = metaSchema.messages;
            var beforeSubmitForApprovalMessage = messages.beforeSubmitForApproval || '';
            var afterSubmitForApprovalMessage = messages.afterSubmitForApproval || '';

            bootbox.confirm(beforeSubmitForApprovalMessage, function(confirmed) {
                if (confirmed) {
                    $osf.postJSON(self.urls.submit.replace('{draft_pk}', self.draft().pk), {}).then(function() {
                        bootbox.dialog({
                            closeButton: false,
                            message: afterSubmitForApprovalMessage,
                            title: 'Pre-Registration Prize Submission',
                            buttons: {
                                registrations: {
                                    label: 'Return to registrations page',
                                    className: 'btn-primary pull-right',
                                    callback: function() {
                                        window.location.href = self.draft.urls.registrations;
                                    }
                                }
                            }
                        });
                    }).fail($osf.growl.bind(null, 'Error submitting for review', language.submitForReviewFail));
                }
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
            schemaData: ctx.node.registrationMetaData[metaSchema.id] || {}
        };
        $osf.applyBindings(metaDataViewModel, '#registrationMetaDataScope');
    }
});
