'use strict';

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var bootbox = require('bootbox');
require('jquery-ui');
require('knockout-sortable');
var lodashGet = require('lodash.get');
var ContribAdder = require('js/contribAdder');
var ContribRemover = require('js/contribRemover');
var osfLanguage = require('js/osfLanguage');

var rt = require('js/responsiveTable');
var $osf = require('./osfHelpers');
require('js/filters');

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

//http://stackoverflow.com/questions/12822954/get-previous-value-of-an-observable-in-subscribe-of-same-observable
ko.subscribable.fn.subscribeChanged = function (callback) {
    var self = this;
    var savedValue = self.peek();
    return self.subscribe(function (latestValue) {
        var oldValue = savedValue;
        savedValue = latestValue;
        callback(latestValue, oldValue);
    });
};

ko.bindingHandlers.filters = {
    init: function(element, valueAccessor, allBindingsAccessor, data, context) {
        var $element = $(element);
        var value = ko.utils.unwrapObservable(valueAccessor()) || {};
        value.callback = data.callback;
        $element.filters(value);
    }
};

// TODO: We shouldn't need both pageOwner (the current user) and currentUserCanEdit. Separate
// out the permissions-related functions and remove currentUserCanEdit.
var ContributorModel = function(contributor, currentUserCanEdit, pageOwner, isRegistration, isParentAdmin, index, options, contribShouter, changeShouter) {

    var self = this;
    self.options = options;
    $.extend(self, contributor);

    self.originals = {
        permission: contributor.permission,
        visible: contributor.visible,
        index: index
    };

    self.toggleExpand = function() {
        self.expanded(!self.expanded());
    };

    self.expanded = ko.observable(false);

    self.filtered = ko.observable(false);

    self.permission = ko.observable(contributor.permission);

    self.permissionText = ko.observable(self.options.permissionMap[self.permission()]);

    self.visible = ko.observable(contributor.visible);

    self.permission.subscribeChanged(function(newValue, oldValue) {
        self.options.onPermissionChanged(newValue, oldValue);
        self.permissionText(self.options.permissionMap[newValue]);
    });

    self.visible.subscribeChanged(function(newValue, oldValue) {
        self.options.onVisibleChanged(newValue, oldValue);
    });

    self.permissionChange = ko.computed(function() {
        return self.permission() !== self.originals.permission;
    });

    self.reset = function(adminCount, visibleCount) {
        if (self.deleteStaged()) {
            if (self.visible()) {
                visibleCount(visibleCount() + 1);
            }
            if (self.permission() === 'admin') {
                adminCount(adminCount() + 1);
            }
            self.deleteStaged(false);
        }
        self.permission(self.originals.permission);
        self.visible(self.originals.visible);
    };

    self.currentUserCanEdit = currentUserCanEdit;
    // User is an admin on the parent project
    self.isParentAdmin = isParentAdmin;

    self.deleteStaged = ko.observable(false);

    self.pageOwner = pageOwner;
    self.contributorToRemove = ko.observable();

    self.contributorToRemove.subscribe(function(newValue) {
        contribShouter.notifySubscribers(newValue, 'contribMessageToPublish');
    });

    self.serialize = function() {
        return JSON.parse(ko.toJSON(self));
    };

    self.canEdit = ko.computed(function() {
        return self.currentUserCanEdit && !self.isParentAdmin;
    });

    self.remove = function() {
        self.contributorToRemove({
            fullname: self.fullname,
            id:self.id});
    };

    self.reInvite = function() {
        $osf.postJSON(
            window.contextVars.node.urls.api + 'contributor/re_invite/',
            {guid: self.id}
        ).done(function(response) {
            $osf.growl(_('Sent'), _('Email will arrive shortly'), 'success');
        }).fail(function(xhr) {
            $osf.growl(_('Error'), _('Invitation failed'), 'danger');
        });
    };

    self.addParentAdmin = function() {
        // Immediately adds parent admin to the component with permissions=read and visible=True
        $osf.block();
        var url = '/api/v1/project/' + window.contextVars.node.id + '/contributors/';
        var userData = self.serialize();
        userData.permission = 'read'; // default permission read
        userData.visible = true; // default visible is true
        return $osf.postJSON(
            url,
            {users: [userData], node_ids: []}
        ).done(function(response) {
            window.location.reload();
        }).fail(function(xhr, status, error){
            $osf.unblock();
            var errorMessage = lodashGet(xhr, 'responseJSON.message') || (sprintf(_('There was a problem trying to add the contributor. ') , osfLanguage.REFRESH_OR_SUPPORT));
            $osf.growl(_('Could not add contributor'), errorMessage);
            Raven.captureMessage(_('Error adding contributors'), {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    };

    self.unremove = function() {
        if (self.deleteStaged()) {
            self.deleteStaged(false);
            self.options.onVisibleChanged(self.visible(), null);
            self.options.onPermissionChanged(self.permission(), null);
        }
        // Allow default action
        return true;
    };
    self.profileUrl = ko.observable(contributor.url);

    self.canRemove = ko.computed(function(){
        return (self.id === pageOwner.id) && !isRegistration && !self.isParentAdmin;
    });

    self.canAddAdminContrib = ko.computed(function() {
        return self.currentUserCanEdit && self.isParentAdmin;
    });

    self.isDirty = ko.pureComputed(function() {
        return self.permissionChange() ||
            self.visible() !== self.originals.visible || self.deleteStaged();
    });

    self.optionsText = function(val) {
        return self.options.permissionMap[val];
    };
};

var MessageModel = function(text, level) {

    var self = this;


    self.text = ko.observable(text || '');
    self.level = ko.observable(level || '');

    var classes = {
        success: 'text-success',
        error: 'text-danger'
    };

    self.cssClass = ko.computed(function() {
        var out = classes[self.level()];
        if (out === undefined) {
            out = '';
        }
        return out;
    });

};

var ContributorsViewModel = function(contributors, adminContributors, user, isRegistration, table, adminTable, contribShouter, pageChangedShouter) {

    var self = this;

    self.original = ko.observableArray(contributors);

    self.table = $(table);
    self.adminTable = $(adminTable);

    self.permissionMap = {
        read: _('Read'),
        write: _('Read + Write'),
        admin: _('Administrator')
    };

    self.permissionList = Object.keys(self.permissionMap);
    self.contributorToRemove = ko.observable('');

    self.contributors = ko.observableArray();

    self.adminContributors = ko.observableArray();

    self.filteredContribs = ko.pureComputed(function() {
        return ko.utils.arrayFilter(self.contributors(), function(item) {
            return item.filtered();
        });
    });

    self.filteredAdmins = ko.pureComputed(function() {
        return ko.utils.arrayFilter(self.adminContributors(), function(item) {
            return item.filtered();
        });
    });

    self.empty = ko.pureComputed(function() {
        return (self.contributors().length - self.filteredContribs().length) === 0;
    });

    self.adminEmpty = ko.pureComputed(function() {
        return (self.adminContributors().length - self.filteredAdmins().length === 0);
    });

    self.callback = function (filtered, empty, activeItems) {
        $.each(activeItems, function (i, contributor) {
            activeItems[i] = ko.dataFor(contributor);
        });
        $.each(self.contributors(), function (i, contributor) {
            contributor.filtered($.inArray(contributor, activeItems) === -1);
        });
        $.each(self.adminContributors(), function (i, contributor) {
            contributor.filtered($.inArray(contributor, activeItems) === -1);
        });
    };

    self.user = ko.observable(user);
    self.canEdit = ko.computed(function() {
        return ($.inArray('admin', user.permissions) > -1) && !isRegistration;
    });

    self.isSortable = ko.computed(function() {
        return self.canEdit() && self.filteredContribs().length === 0;
    });

    // Hack: Ignore beforeunload when submitting
    // TODO: Single-page-ify and remove this
    self.forceSubmit = ko.observable(false);

    self.changed = ko.computed(function() {
        for (var i = 0, contributor; contributor = self.contributors()[i]; i++) {
            if (contributor.isDirty() || contributor.originals.index !== i){
                return true;
            }
        }
        return false;
    });

    self.retainedContributors = ko.computed(function() {
        return ko.utils.arrayFilter(self.contributors(), function(item) {
            return !item.deleteStaged();
        });
    });

    self.adminCount = ko.observable(0);

    self.visibleCount = ko.observable(0);

    self.canSubmit = ko.computed(function() {
        return self.changed() && self.adminCount() && self.visibleCount();
    });

    self.changed.subscribe(function(newValue) {
        pageChangedShouter.notifySubscribers(newValue, 'changedMessageToPublish');
    });

    self.messages = ko.computed(function() {
        var messages = [];
        if(!self.adminCount()) {
            messages.push(
                new MessageModel(
                    _('Must have at least one registered admin contributor'),
                    'error'
                )
            );
        }
        if (!self.visibleCount()) {
            messages.push(
                new MessageModel(
                    _('Must have at least one bibliographic contributor'),
                    'error'
                )
            );
        }
        return messages;
    });

    self.handlePermissionChanged = function(newPerm, oldPerm) {
        if (oldPerm === 'admin') {
            self.adminCount(self.adminCount() - 1);
        }
        if (newPerm === 'admin') {
            self.adminCount(self.adminCount() + 1);
        }
    };

    self.handleVisibleChanged = function(newVis, oldVis) {
        if (oldVis) {
            self.visibleCount(self.visibleCount() - 1);
        }
        if (newVis) {
            self.visibleCount(self.visibleCount() + 1);
        }
    };

    self.options = {
        onPermissionChanged: self.handlePermissionChanged,
        onVisibleChanged: self.handleVisibleChanged,
        permissionMap: self.permissionMap
    };

    self.init = function() {
        var index = -1;
        self.contributors(self.original().map(function(item) {
            index++;
            if (item.permission === 'admin') {
                self.adminCount(self.adminCount() + 1);
            }
            if (item.visible) {
                self.visibleCount(self.visibleCount() + 1);
            }
            return new ContributorModel(item, self.canEdit(), self.user(), isRegistration, false, index, self.options, contribShouter, pageChangedShouter);
        }));
        self.adminContributors(adminContributors.map(function(contributor) {
          if (contributor.permission === 'admin') {
                self.adminCount(self.adminCount() + 1);
            }
          return new ContributorModel(contributor, self.canEdit(), self.user(), isRegistration, true, index, self.options, contribShouter, pageChangedShouter);
        }));
    };

    // Warn on add contributors if pending changes
    $('[href="#addContributors"]').on('click', function() {
        if (self.changed()) {
            $osf.growl('Error:',
                    _('Your contributor list has unsaved changes. Please ') +
                    _('save or cancel your changes before adding ') +
                    _('contributors.')
            );
            return false;
        }
    });
    // Warn on URL change if pending changes
    $(window).bind('beforeunload', function() {
        if (self.changed() && !self.forceSubmit()) {
            // TODO: Use GrowlBox.
            return _('There are unsaved changes to your contributor settings');
        }
    });

    self.init();

    self.serialize = function() {
        return ko.utils.arrayMap(
            ko.utils.arrayFilter(self.contributors(), function(contributor) {
                return !contributor.deleteStaged();
            }),
            function(contributor) {
                return contributor.serialize();
            }
        );
    };

    self.cancel = function() {
        self.contributors().forEach(function(contributor) {
            contributor.reset(self.adminCount, self.visibleCount);
        });
        self.contributors(self.contributors().sort(function(left, right) {
            return left.originals.index > right.originals.index ? 1 : -1;
        }));
    };

    self.submit = function() {
        self.forceSubmit(true);
        bootbox.confirm({
            title: _('Save changes?'),
            message: _('Are you sure you want to save these changes?'),
            callback: function(result) {
                if (result) {
                    $osf.postJSON(
                        window.contextVars.node.urls.api + 'contributors/manage/',
                        {contributors: self.serialize()}
                    ).done(function(response) {
                        // TODO: Don't reload the page here; instead use code below
                        if (response.redirectUrl) {
                            window.location.href = response.redirectUrl;
                        } else {
                            window.location.reload();
                        }
                    }).fail(function(xhr) {
                        var response = xhr.responseJSON;
                        $osf.growl('Error:',
                            _('Submission failed: ') + response.message_long
                        );
                        self.forceSubmit(false);
                    });
                }
            },
            buttons:{
                confirm:{
                    label:_('Save'),
                    className:'btn-success'
                },
                cancel:{
                    label:_('Cancel')
                }
            }
        });
    };

    self.afterRender = function(elements, data) {
        var table;
        if (data === 'contrib') {
            table = self.table[0];
        }
        else if (data === 'admin') {
            table = self.adminTable[0];
        }
        if (!!table) {
            rt.responsiveTable(table);
        }
    };

    self.collapsed = ko.observable(true);

    self.onWindowResize = function() {
        self.collapsed(self.table.children().filter('thead').is(':hidden'));
    };

};

////////////////
// Public API //
////////////////

function ContribManager(selector, contributors, adminContributors, user, isRegistration, table, adminTable) {
    var self = this;
    //shouter allows communication between ContribManager and ContribRemover, in particular which contributor needs to
    // be removed is passed to ContribRemover
    var contribShouter = new ko.subscribable();
    var pageChangedShouter = new ko.subscribable();
    self.selector = selector;
    self.$element = $(selector);
    self.contributors = contributors;
    self.adminContributors = adminContributors;
    self.viewModel = new ContributorsViewModel(contributors, adminContributors, user, isRegistration, table, adminTable, contribShouter, pageChangedShouter);
    $('body').on('nodeLoad', function(event, data) {
        // If user is a contributor, initialize the contributor modal
        // controller

        var treeDataPromise = $.ajax({
            url: window.contextVars.node.urls.api + 'tree/',
            type: 'GET',
            dataType: 'json',
        });
        if (data.user.can_edit) {
            new ContribAdder(
                '#addContributors',
                data.node.title,
                data.node.id,
                data.parent_node.id,
                data.parent_node.title,
                treeDataPromise
            );
        }
        if (data.user.can_edit || data.user.is_contributor) {
            new ContribRemover(
                '#removeContributor',
                data.node.title,
                data.node.id,
                data.user.username,
                data.user.id,
                contribShouter,
                pageChangedShouter,
                treeDataPromise
            );
        }
    });
    self.init();
}

ContribManager.prototype.init = function() {
    $osf.applyBindings(this.viewModel, this.$element[0]);
    this.$element.show();
};

module.exports = ContribManager;
