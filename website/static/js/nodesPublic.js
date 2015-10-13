/**
 * Controller for the Add Contributor modal.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var oop = require('./oop');
var $osf = require('./osfHelpers');
var Paginator = require('./paginator');
var osfHelpers = require('js/osfHelpers');


var NODE_OFFSET = 25;

var MESSAGES = {
    makeProjectPublicWarning: 'Please review your project for sensitive or restricted information before making it public.  ' +
                        'Once a project is made public, you should assume it will always be public. You can ' +
                        'return it to private later, but search engines or others may access files before you do so.  ' +
                        'Are you sure you would like to continue?',

    makeProjectPrivateWarning: 'Making a project private will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Would you like to continue?',

    makeComponentPublicWarning: '<p>Please review your component for sensitive or restricted information before making it public.</p>' +
                        'Once a component is made public, you should assume it will always be public. You can ' +
                        'return it to private later, but search engines or others may access files before you do so.  ' +
                        'Are you sure you would like to continue?',

    makeComponentPrivateWarning: 'Making a component private will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Would you like to continue?',

    makeRegistrationPublicWarning: 'Once a registration is made public, you will not be able to make the ' +
                        'registration private again.  After making the registration public, if you '  +
                        'discover material in it that should have remained private, your only option ' +
                        'will be to retract the registration.  This will eliminate the registration, ' +
                        'leaving only basic information of the project title, description, and '  +
                        'contributors with a notice of retraction.'
};



var NodesPublicViewModel = function() {
    var self = this;
    self.page = ko.observable('warning');
    self.pageTitle = ko.computed(function() {
        return {
            warning: 'Warning',
            which: 'Select Components',
            invite: 'Add Unregistered Contributor'
        }[self.page()];
    });
    self.message = ko.observable(MESSAGES.makeProjectPublicWarning);
};

function NodesPublic (selector, data, options) {
    var self = this;
    self.selector = selector;
    self.$element = $(self.selector);
    self.data = data;
    self.viewModel = new NodesPublicViewModel(self.data);
    self.init();
}

NodesPublic.prototype.init = function() {
    var self = this;
    osfHelpers.applyBindings(self.viewModel, this.selector);
};

module.exports = {
    _ProjectViewModel: NodesPublicViewModel,
    NodesPublic: NodesPublic
};
