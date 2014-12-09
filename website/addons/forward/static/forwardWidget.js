
'use strict';
var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var $osf = require('osf-helpers');

ko.punches.enableAll();

/**
 * Knockout view model for the Forward node settings widget.
 */
var ViewModel = function(url) {

    var self = this;

    self.url = ko.observable();
    self.label = ko.observable();
    self.linkDisplay = ko.computed(function() {
        if (self.label()) {
            return self.label();
        } else {
            return self.url();
        }
    });
    self.redirectBool = ko.observable();
    self.redirectSecs = ko.observable();

    self.interval = null;
    self.redirecting = ko.observable();
    self.timeLeft = ko.observable();

    self.doRedirect = function() {
        window.location.href = self.url();
    };

    self.tryRedirect = function() {
        if (self.timeLeft() > 0) {
            self.timeLeft(self.timeLeft() - 1);
        } else {
            self.doRedirect();
        }
    };

    self.queueRedirect = function() {
        self.redirecting(true);
        $.blockUI({message: $('#forwardModal')});
        self.timeLeft(self.redirectSecs());
        self.interval = setInterval(
            self.tryRedirect,
            1000
        );
    };

    self.cancelRedirect = function() {
        self.redirecting(false);
        $.unblockUI();
        clearInterval(self.interval);
    };

    self.execute = function() {
        if (self.redirectBool()) {
            self.queueRedirect();
        }
    };

    self.init = function() {
        $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json',
            success: function(response) {
                self.url(response.url);
        self.label(response.label);
                self.redirectBool(response.redirectBool);
                self.redirectSecs(response.redirectSecs);
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

