'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
require('jquery-ui');
require('knockout-sortable');

var rt = require('js/responsiveTable');
var $osf = require('./osfHelpers');
require('js/filters');

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
        value.callback = function (filtered, empty, activeItems) {
            $.each(activeItems, function (i, contributor) {
                activeItems[i] = ko.dataFor(contributor);
            });
            $.each(data.contributors(), function (i, contributor) {
                contributor.filtered($.inArray(contributor, activeItems) === -1);
            });
            $.each(data.adminContributors(), function (i, contributor) {
                contributor.filtered($.inArray(contributor, activeItems) === -1);
            });
        };
        $element.filters(value);
    }
};

// TODO: We shouldn't need both pageOwner (the current user) and currentUserCanEdit. Separate
// out the permissions-related functions and remove currentUserCanEdit.
var ContributorModel = function(contributor, currentUserCanEdit, pageOwner, isRegistration, isAdmin, index, parent) {

    var self = this;
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

    self.permissionText = ko.observable(parent.permissionDict[self.permission()]);

    self.visible = ko.observable(contributor.visible);

    self.permission.subscribeChanged(function(newValue, oldValue) {
        if (oldValue === 'admin') {
            parent.adminCount(parent.adminCount() - 1);
        }
        if (newValue === 'admin') {
            parent.adminCount(parent.adminCount() + 1);
        }
        self.permissionText(parent.permissionDict[newValue]);
    });

    self.visible.subscribeChanged(function(newValue, oldValue) {
        if (oldValue === true) {
            parent.visibleCount(parent.visibleCount() - 1);
        }
        if (newValue === true) {
            parent.visibleCount(parent.visibleCount() + 1);
        }
    });

    self.permissionChange = ko.computed(function() {
        return self.permission() !== self.originals.permission;
    });

    self.reset = function() {
        if (self.deleteStaged()) {
            if (self.visible()) {
                parent.visibleCount(parent.visibleCount() + 1);
            }
            if (self.permission() === 'admin') {
                parent.adminCount(parent.adminCount() + 1);
            }
            self.deleteStaged(false);
        }
        self.permission(self.originals.permission);
        self.visible(self.originals.visible);
    };

    self.currentUserCanEdit = currentUserCanEdit;
    self.isAdmin = isAdmin;

    self.deleteStaged = ko.observable(false);

    self.pageOwner = pageOwner;

    self.serialize = function() {
        return JSON.parse(ko.toJSON(self));
    };

    self.canEdit = ko.computed(function() {
        return self.currentUserCanEdit && !self.isAdmin;
    });

    self.remove = function() {
        if (parent.visibleCount() > 0 && self.visible()) {
            parent.visibleCount(parent.visibleCount() - 1);
        }
        if (parent.adminCount() > 0 && self.permission() === 'admin') {
            parent.adminCount(parent.adminCount() - 1);
        }
        self.deleteStaged(true);
    };
    self.unremove = function() {
        if (self.deleteStaged()) {
            self.deleteStaged(false);
            if (self.visible()) {
                parent.visibleCount(parent.visibleCount() + 1);
            }
            if (self.permission() === 'admin') {
                parent.adminCount(parent.adminCount() + 1);
            }
        }
        // Allow default action
        return true;
    };
    self.profileUrl = ko.observable(contributor.url);

    self.canRemove = ko.computed(function(){
        return (self.id === pageOwner.id) && !isRegistration;
    });

    self.isDirty = ko.pureComputed(function() {
        return self.permissionChange() ||
            self.visible() !== self.originals.visible || self.deleteStaged();
    });

    // TODO: copied-and-pasted from nodeControl. When nodeControl
    // gets refactored, update this to use global method.
    self.removeSelf = function() {
        var id = self.id,
            name = self.fullname;
        var payload = {
            id: id,
            name: self.fullname
        };

        if (parent.visibleCount() > 0 && self.visible()) {
            parent.visibleCount(parent.visibleCount() - 1);
        }

        if (parent.visibleCount() > 0) {
            $osf.postJSON(
                window.contextVars.node.urls.api + 'beforeremovecontributors/',
                payload
            ).done(function (response) {
                    bootbox.confirm({
                        title: 'Delete contributor?',
                        message: ('Are you sure you want to remove yourself (<strong>' + name + '</strong>) from contributor list?'),
                        callback: function (result) {
                            if (result) {
                                $osf.postJSON(
                                    window.contextVars.node.urls.api + 'removecontributors/',
                                    payload
                                ).done(function (response) {
                                        if (response.redirectUrl) {
                                            window.location.href = response.redirectUrl;
                                        } else {
                                            window.location.reload();
                                        }
                                    }).fail(
                                    $osf.handleJSONError
                                );
                            }
                        },
                        buttons:{
                            confirm:{
                                label:'Delete',
                                className:'btn-danger'
                            }
                        }
                    });
                }).fail(
                $osf.handleJSONError
            );
            return false;
        }
    };

    self.optionsText = function(val) {
        return parent.permissionDict[val];
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

var ContributorsViewModel = function(contributors, adminContributors, user, isRegistration, table, adminTable) {

    var self = this;

    self.original = ko.observableArray(contributors);

    self.table = $(table);
    self.adminTable = $(adminTable);

    self.permissionDict = {
        read: 'Read',
        write: 'Read + Write',
        admin: 'Administrator'
    };

    self.permissionList = Object.keys(self.permissionDict);

    self.contributors = ko.observableArray();

    self.adminContributors = ko.observableArray();

    self.filteredContribs = ko.computed(function() {
        return ko.utils.arrayFilter(self.contributors(), function(item) {
            return item.filtered();
        });
    });

    self.filteredAdmins = ko.computed(function() {
        return ko.utils.arrayFilter(self.adminContributors(), function(item) {
            return item.filtered();
        });
    });

    self.empty = ko.computed(function() {
        return (self.contributors().length - self.filteredContribs().length) === 0;
    });

    self.adminEmpty = ko.computed(function() {
        return (self.adminContributors().length - self.filteredAdmins().length === 0);
    });

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

    self.messages = ko.computed(function() {
        var messages = [];
        if(!self.adminCount()) {
            messages.push(
                new MessageModel(
                    'Must have at least one registered admin contributor',
                    'error'
                )
            );
        }
        if (!self.visibleCount()) {
            messages.push(
                new MessageModel(
                    'Must have at least one bibliographic contributor',
                    'error'
                )
            );
        }
        return messages;
    });

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
            return new ContributorModel(item, self.canEdit(), self.user(), isRegistration, false, index, self);
        }));
        self.adminContributors(adminContributors.map(function(contributor) {
          if (contributor.permission === 'admin') {
                self.adminCount(self.adminCount() + 1);
            }
          return new ContributorModel(contributor, self.canEdit(), self.user(), isRegistration, true, index, self);
        }));
    };

    // Warn on add contributors if pending changes
    $('[href="#addContributors"]').on('click', function() {
        if (self.changed()) {
            $osf.growl('Error:',
                    'Your contributor list has unsaved changes. Please ' +
                    'save or cancel your changes before adding ' +
                    'contributors.'
            );
            return false;
        }
    });
    // Warn on URL change if pending changes
    $(window).bind('beforeunload', function() {
        if (self.changed() && !self.forceSubmit()) {
            // TODO: Use GrowlBox.
            return 'There are unsaved changes to your contributor settings';
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
            contributor.reset();
        });
        self.contributors(self.contributors.sort(function(left, right) {
            return left.originals.index > right.originals.index ? 1 : -1;
        }));
    };

    self.submit = function() {
        self.forceSubmit(true);
        bootbox.confirm({
            title: 'Save changes?',
            message: 'Are you sure you want to save these changes?',
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
                            'Submission failed: ' + response.message_long
                        );
                        self.forceSubmit(false);
                    });
                }
            },
            buttons:{
                confirm:{
                    label:'Save',
                    className:'btn-success'
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

    self.checkWindowWidth = function() {
        self.collapsed(self.table.children().filter('thead').is(':hidden'));
        self.table.find('tbody>tr').css('display', '');
    };
};

////////////////
// Public API //
////////////////

function ContribManager(selector, contributors, adminContributors, user, isRegistration, table, adminTable) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.contributors = contributors;
    self.adminContributors = adminContributors;
    self.viewModel = new ContributorsViewModel(contributors, adminContributors, user, isRegistration, table, adminTable);
    self.init();
}

ContribManager.prototype.init = function() {
    ko.applyBindings(this.viewModel, this.$element[0]);
    this.$element.show();
};

module.exports = ContribManager;
