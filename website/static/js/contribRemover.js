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

var API_BASE = 'http://localhost:8000/v2/nodes/';


var RemoveContributorViewModel = oop.extend(Paginator, {
    constructor: function(title, nodeId, parentId, parentTitle, userName, shouter) {
        this.super.constructor.call(this);
        var self = this;

        self.title = title;
        self.nodeId = nodeId;
        self.nodeApiUrl = '/api/v1/project/' + self.nodeId + '/';
        self.parentId = parentId;
        self.parentTitle = parentTitle;

        this.contributorToRemove = ko.observable();
        shouter.subscribe(function(newValue) {
            console.log('shouter newvalue is ' + newValue);
            this.contributorToRemove(newValue);
        }, this, "messageToPublish");

        self.page = ko.observable('remove');
        self.pageTitle = ko.computed(function() {
            return {
                remove: 'Delete Contributors',
            }[self.page()];
        });
        self.userName = ko.observable(userName);
        self.deleteAll = ko.observable(false);
        //self.query = ko.observable();
        //self.results = ko.observableArray([]);
        //self.contributors = ko.observableArray([]);
        //self.selection = ko.observableArray();
        //self.notification = ko.observable('');
        //self.inviteError = ko.observable('');
        //self.totalPages = ko.observable(0);
        //self.nodes = ko.observableArray([]);
        //self.nodesToChange = ko.observableArray();
        //
        //self.foundResults = ko.pureComputed(function() {
        //    return self.query() && self.results().length;
        //});
        //
        //self.noResults = ko.pureComputed(function() {
        //    return self.query() && !self.results().length;
        //});
        //
        //self.addAllVisible = ko.pureComputed(function() {
        //    var selected_ids = self.selection().map(function(user){
        //        return user.id;
        //    });
        //    for(var i = 0; i < self.results().length; i++) {
        //        if(self.contributors().indexOf(self.results()[i].id) === -1 &&
        //           selected_ids.indexOf(self.results()[i].id) === -1) {
        //            return true;
        //        }
        //    }
        //    return false;
        //});
        //
        //self.removeAllVisible = ko.pureComputed(function() {
        //    return self.selection().length > 0;
        //});
        //
        //self.inviteName = ko.observable();
        //self.inviteEmail = ko.observable();
        //
        //self.addingSummary = ko.computed(function() {
        //    var names = $.map(self.selection(), function(result) {
        //        return result.fullname;
        //    });
        //    return names.join(', ');
        //});
    },
    selectRemove: function() {
        var self = this;
        self.page('remove');
    },
    selectWhich: function() {
        this.page('which');
    },
    gotoInvite: function() {
        var self = this;
        self.inviteName(self.query());
        self.inviteError('');
        self.inviteEmail('');
        self.page('invite');
    },
    clear: function() {
        var self = this;
        self.selectRemove();
        self.deleteAll(false);
    },
    submit: function() {
        var self = this;
        debugger;
            //var url = API_BASE + "chd2w";
            var url = 'http://localhost:8000/v2/nodes/tpy9k/contributors/k7j3u/';
        $.ajax({
            url: url,
            type: 'DELETE',
            dataType: 'json',
            contentType: 'application/json',
            crossOrigin: true,
            xhrFields: {withCredentials: true},
            processData: false,
            data: JSON.stringify(
                {
                    'data': {
                        'type': 'contributors',
                        'id': 'k7j3u'
                    }
                })
        }).done(function (response) {
            window.location.reload();
        }).fail(function (xhr, status, error) {
            $osf.growl('Error', 'Unable to delete Contributor');
            Raven.captureMessage('Could not DELETE Contributor.', {
                API_BASE: url, status: status, error: error
            });
        });

        self.page('remove');
    },
    //deleteAll: function() {
    //    var self = this;
    //    self.deleteAll(true);
    //},

});


////////////////
// Public API //
////////////////

function ContribRemover(selector, nodeTitle, nodeId, parentId, parentTitle, userName, shouter) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.nodeTitle = nodeTitle;
    self.nodeId = nodeId;
    self.parentId = parentId;
    self.parentTitle = parentTitle;
    self.userName = userName;
    self.viewModel = new RemoveContributorViewModel(self.nodeTitle,
        self.nodeId, self.parentId, self.parentTitle, self.userName, shouter);
    self.init();
}

ContribRemover.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
    // Clear popovers on dismiss start
    self.$element.on('hide.bs.modal', function() {
        self.$element.find('.popover').popover('hide');
    });
    // Clear user search modal when dismissed; catches dismiss by escape key
    // or cancel button.
    self.$element.on('hidden.bs.modal', function() {
        self.viewModel.clear();
    });
};

module.exports = ContribRemover;
