/**
 *
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout'], factory);
    } else {
        global.NewPreprint = factory(jQuery, ko);
        $script.done('newPreprint');
    }
}(this, function($, ko){

    'use strict';

    var ViewModel = function(submitUrl) {

        var self = this;

        self.paperName = ko.observable('').extend({
            required: true,
            minLength: 3
        });
        self.file = ko.observable();

        // Preserve object of validated fields for use in `submit`
        var validatedFields = {
            paperName: self.paperName,
        };
        // Collect validated fields
        self.validatedFields = ko.validatedObservable($.extend({}, validatedFields));

        self.showValidation = ko.observable(false);
        self.submitted = ko.observable(false);

        self.flashMessage = ko.observable();
        self.flashMessageClass = ko.observable();
        self.flashTimeout = null;

        self.trim = function(observable) {
            observable($.trim(observable()));
        };

        /** Change the flashed message. */
        self.changeMessage = function(message, messageClass, text, css, timeout, timeoutClock) {
            message(text);
            var cssClass = css || 'text-info';
            messageClass(cssClass);
            if (timeout) {
                // Reset message after timeout period
                if (timeoutClock) {
                    clearTimeout(timeoutClock);
                }
                self.timeout = setTimeout(
                    function() {
                        message('');
                        messageClass('text-info');
                    },
                    timeout
                );
            }
        };

        self.isValid = ko.computed(function() {
            return self.validatedFields.isValid();
        });

        self.submitSuccess = function(response) {
            self.changeMessage(
                self.flashMessage,
                self.flashMessageClass,
                response.message,
                'text-info'
            );
            self.submitted(true);
        };

        self.submitError = function(xhr) {
            self.changeMessage(
                self.flashMessage,
                self.flashMessageClass,
                xhr.responseJSON.message_long,
                'text-danger',
                5000,
                self.flashTimeout
            );
        };

        self.hideValidation = function() {
            self.showValidation(false);
        };

        self.submit = function() {
            // Show errors if invalid
            if (!self.isValid()) {
                // Ensure validation errors are displayed
                $.each(validatedFields, function(key, value) {
                    value.notifySubscribers();
                });
                self.showValidation(true);
                return;
            }
            // Else submit
            $.ajax({
                type: 'POST',
                url: submitUrl,
                data: ko.toJSON(self),
                contentType: 'application/json',
                dataType: 'json',
                success: self.submitSuccess,
                error: self.submitError
            });
        };

    };

    var NewPreprint = function(selector, submitUrl) {
        this.viewModel = new ViewModel(submitUrl);
        $.osf.applyBindings(this.viewModel, selector);
        window.vm = this.viewModel;
    };

    return NewPreprint;

}));
