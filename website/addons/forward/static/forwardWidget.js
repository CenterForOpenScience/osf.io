'use strict';

var ko = require('knockout');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

/**
 * Knockout view model for the Forward node settings widget.
 */
var ViewModel = function(url) {

    var self = this;

    self.url = ko.observable();
    self.label = ko.observable();
    self.isRegistration = ko.observable();
    self.linkDisplay = ko.computed(function() {
        if (self.label()) {
            return self.label();
        } else {
            return self.url();
        }
    });

    self.redirecting = ko.observable();

    self.doRedirect = function() {
        window.location.href = self.url();
    };

    self.queueRedirect = function() {
        self.redirecting(true);
        if (!self.isRegistration()) {
            $.blockUI({message: $('#forwardModal')});
        }
    };

    self.cancelRedirect = function() {
        self.redirecting(false);
        $.unblockUI();
    };

    self.execute = function() {
        self.queueRedirect();
    };

    self.init = function() {
        $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json',
            success: function(response) {
                self.url(response.url);
                self.isRegistration(response.is_registration);
                self.label(response.label);
                self.execute();
            }
        });
    };
};

// Public API
function ForwardWidget(selector, url) {
    var self = this;
    self.viewModel = new ViewModel(url);
    $osf.applyBindings(self.viewModel, selector);
    self.viewModel.init();
}

module.exports = ForwardWidget;

