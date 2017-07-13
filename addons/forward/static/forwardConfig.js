'use strict';

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var koHelpers = require('js/koHelpers');
var $osf = require('js/osfHelpers');

var MESSAGE_TIMEOUT = 5000;

/**
 * Knockout view model for the Forward node settings widget.
 */
var ViewModel = function(node, enabled, url, label) {

    var self = this;

    var forwardUrl = $osf.apiV2Url('nodes/' + node.id + '/addons/forward/');

    self.enabled = ko.observable(enabled);
    self.label = koHelpers.sanitizedObservable(label);
    self.url = ko.observable(url).extend({
        ensureHttp: true,
        url: true,
        required: true
    });

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    self.pendingRequest = ko.observable(false);

    ko.validation.addAnonymousRule(
        self.url,
        koHelpers.makeRegexValidator(
            new RegExp(nodeId, 'i'),
            'Components cannot link to themselves',
            false
        )
    );

    self.validators = ko.validatedObservable({
        url: self.url,
    });

    self.enabled.subscribe(function(newValue) {
        self.pendingRequest(true);
        if (!newValue) {
            $osf.ajaxJSON(
                'delete',
                forwardUrl,
                {'isCors': true}
            ).done(function(response) {
                self.pendingRequest(false);
            }).fail(function(xhr, status, error) {
                $osf.growl('Error', 'Unable to disable redirect link.');
                Raven.captureMessage('Error disabling redirect link.', {
                    extra: {
                        url: forwardUrl, status: status, error: error
                    }
                });
            });
        } else {
            $osf.ajaxJSON(
                'post',
                forwardUrl,
                {
                    'data': {
                        'data': {
                            'id': 'forward',
                            'type': 'node_addons',
                            'attributes': {}
                        }
                    },
                    'isCors': true
                }
            ).done(function(response) {
                self.pendingRequest(false);
            }).fail(function(xhr, status, error) {
                $osf.growl('Error', 'Unable to enable redirect link.');
                Raven.captureMessage('Error enabling redirect link.', {
                    extra: {
                        url: forwardUrl, status: status, error: error
                    }
                });
            });
        }
    });

    function onSubmitSuccess() {
        if (self.url() == null) {
            self.changeMessage(
                'Please fill in the required field.',
                'text-danger'
            );
        }
        else {
            self.changeMessage(
                'Successfully linked to <a href="' + self.url() + '">' + self.url() + '</a>.',
                'text-success',
                MESSAGE_TIMEOUT
            );
        }
    }

    function onSubmitError(xhr, status) {
        var re = /^(https?):\/{2}/;
        var b = self.url().replace(re, '');
        if (b == '') {
            self.changeMessage(
                'Please fill in the required field.',
                'text-danger'
            );
        }
        else {
            self.changeMessage(
                'Could not change redirect link settings. Please try again later.',
                'text-danger'
            );
            Raven.captureMessage('Error updating redirect link.', {
                extra: {
                    url: forwardUrl, status: status, error: error
                }
            });
        }
    }

    /**
     * Submit new settings.
     */
    self.submitSettings = function() {
        self.pendingRequest(true);
        $osf.ajaxJSON(
            'put',
            forwardUrl,
            {
                'data': {
                    'data': {
                        'id': 'forward',
                        'type': 'node_addons',
                        'attributes': {
                            'url': self.url(),
                            'label': self.label()
                        }
                    }
                },
                'isCors': true
            }
        ).done(function(response) {
            onSubmitSuccess()
            self.pendingRequest(false);
        }).fail(function(response) {
            onSubmitError()
            self.pendingRequest(false);
        });
    };

    /** Change the flashed message. */
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

};

// Public API
function ForwardConfig(selector, node, enabled, url, label) {
    var self = this;
    self.viewModel = new ViewModel(node, enabled, url, label);
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = ForwardConfig;

