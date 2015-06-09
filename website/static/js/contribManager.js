'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
require('jquery-ui');
require('knockout-sortable');

var $osf = require('./osfHelpers');

var contribsEqual = function(a, b) {
    return a.id === b.id &&
        a.visible === b.visible &&
        a.permission === b.permission &&
        Boolean(a.deleteStaged) === Boolean(b.deleteStaged);
};

// Modified from http://stackoverflow.com/questions/7837456/comparing-two-arrays-in-javascript
var arraysEqual = function(a, b) {
    var i = a.length;
    if (i !== b.length) { return false;}
    while (i--) {
        if (!contribsEqual(a[i], b[i])) {return false;}
    }
    return true;
};

var sortMap = {
    surname: {
        label: 'Surname',
        order: 1,
        func: function(item) {
            return item.surname;
        }
    }
};

// TODO: We shouldn't need both pageOwner (the current user) and currentUserCanEdit. Separate
// out the permissions-related functions and remove currentUserCanEdit.
var ContributorModel = function(contributor, currentUserCanEdit, pageOwner, isRegistration, isAdmin) {

    var self = this;
    $.extend(self, contributor);

    self.permissionList = [
        {value: 'read', text: 'Read'},
        {value: 'write', text: 'Read + Write'},
        {value: 'admin', text: 'Administrator'}
    ];
    self.getPermission = function(permission) {
        for(var i = 0; i < self.permissionList.length; i++) {
            if(permission === self.permissionList[i].value) {
                return self.permissionList[i];
            }
        }
        return self.permissionList[0];
    };

    self.currentUserCanEdit = currentUserCanEdit;
    self.isAdmin = isAdmin;
    self.visible = ko.observable(contributor.visible);
    self.permission = ko.observable(contributor.permission);
    self.curPermission = ko.observable(self.getPermission(self.permission()));
    self.deleteStaged = ko.observable(contributor.deleteStaged || false);
    self.removeContributor = 'Remove contributor';
    self.pageOwner = pageOwner;
    self.serialize = function() {
        return JSON.parse(ko.toJSON(self));
    };

    self.canEdit = ko.computed(function() {
      return self.currentUserCanEdit && !self.isAdmin;
    });

    self.remove = function() {
        self.deleteStaged(true);
    };
    self.unremove = function(data, event) {
        var $target = $(event.target);
        if (!$target.hasClass('contrib-button')) {
            self.deleteStaged(false);
        }
        // Allow default action
        return true;
    };
    self.profileUrl = ko.observable(contributor.url);
    self.notDeleteStaged = ko.computed(function() {
        return !self.deleteStaged();
    });
    self.formatPermission = ko.computed(function() {
        var permission = self.permission();
        return self.getPermission(permission).text;
    });

    self.canRemove = ko.computed(function(){
        return (self.id === pageOwner.id) && !isRegistration;
    });

    self.change = ko.pureComputed(function() {
        self.permission(self.curPermission().value);
        var currentValue = self.curPermission().value;
        return currentValue === self.original;
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
        $osf.postJSON(
            nodeApiUrl + 'beforeremovecontributors/',
            payload
        ).done(function(response) {
            var prompt = $osf.joinPrompts(response.prompts, 'Remove <strong>' + name + '</strong> from contributor list?');
            bootbox.confirm({
                title: 'Delete Contributor?',
                message: prompt,
                callback: function(result) {
                    if (result) {
                        $osf.postJSON(
                            nodeApiUrl + 'removecontributors/',
                            payload
                        ).done(function(response) {
                            if (response.redirectUrl) {
                                window.location.href = response.redirectUrl;
                            } else {
                                window.location.reload();
                            }
                        }).fail(
                            $osf.handleJSONError
                        );
                    }
                }
            });
        }).fail(
            $osf.handleJSONError
        );
        return false;
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

var ContributorsViewModel = function(contributors, adminContributors, user, isRegistration) {

    var self = this;

    self.original = ko.observableArray(contributors);

    self.contributors = ko.observableArray();
    self.adminContributors = adminContributors;

    self.user = ko.observable(user);
    // TODO: Does this need to be an observable?
    self.userIsAdmin  = ko.observable($.inArray('admin', user.permissions) !== -1);
    self.canEdit = ko.computed(function() {
        return (self.userIsAdmin()) && !isRegistration;
    });

    self.messages = ko.observableArray([]);

    // Hack: Ignore beforeunload when submitting
    // TODO: Single-page-ify and remove this
    self.forceSubmit = ko.observable(false);

    self.sortKeys = Object.keys(sortMap);
    self.sortKey = ko.observable(self.sortKeys[0]);
    self.sortOrder = ko.observable(0);
    self.sortClass = ko.computed(function() {
        if (self.sortOrder() === 1) {
                return 'fa fa-caret-up';
        } else if (self.sortOrder() === -1) {
                return 'fa fa-caret-down';
        }
    });
    self.sortFunc = ko.computed(function() {
        return sortMap[self.sortKey()].func;
    });
    self.sortKey.subscribe(function() {
        self.sortOrder(0);
    });

    self.changed = ko.computed(function() {
        var contributorData = ko.utils.arrayMap(self.contributors(), function(item) {
            return item.serialize();
        });
        return !arraysEqual(contributorData, self.original());
    });

    self.retainedContributors = ko.computed(function() {
        return ko.utils.arrayFilter(self.contributors(), function(item) {
            return !item.deleteStaged();
        });
    });
    self.validAdmin = ko.computed(function() {
        var admins = ko.utils.arrayFilter(self.retainedContributors(), function(item) {
            return item.permission() === 'admin' &&
                item.registered;
        });
        return !!admins.length;
    });
    self.validVisible = ko.computed(function() {
        return ko.utils.arrayFilter(self.retainedContributors(), function(item) {
            return item.visible();
        }).length;
    });

    self.canSubmit = ko.computed(function() {
        return self.changed() && self.validAdmin() && self.validVisible();
    });
    self.changed.subscribe(function() {
        self.messages([]);
    });

    self.validAdmin.subscribe(function(value) {
        if (!value) {
            self.messages.push(
                new MessageModel(
                    'Must have at least one registered admin contributor',
                    'error'
                )
            );
        } else {
            self.messages([]);
        }
    });
    self.validVisible.subscribe(function(value) {
        if (!value) {
            self.messages.push(
                new MessageModel(
                    'Must have at least one visible contributor',
                    'error'
                )
            );
        }
    });

    self.init = function() {
        self.messages([]);
        self.contributors(self.original().map(function(item) {
            return new ContributorModel(item, self.canEdit(), self.user(), isRegistration);
        }));
        self.adminContributors = adminContributors.map(function(contributor) {
          return new ContributorModel(contributor, self.canEdit(), self.user(), isRegistration, true);
        });
    };

    self.initListeners = function() {
        var self = this;
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
        $(window).on('beforeunload', function() {
            if (self.changed() && !self.forceSubmit()) {
                // TODO: Use GrowlBox.
                return 'There are unsaved changes to your contributor ' +
                    'settings. Are you sure you want to leave this page?';
            }
        });
    };

    self.init();
    self.initListeners();

    self.sort = function() {
        if (self.sortOrder() === 0) {
            self.sortOrder(sortMap[self.sortKey()].order);
        } else {
            self.sortOrder(-1 * self.sortOrder());
        }
        var func = sortMap[self.sortKey()].func;
        var comparator = function(left, right) {
            var leftVal = func(left);
            var rightVal = func(right);
            var spaceship = leftVal === rightVal ?
                0 :
                (leftVal < rightVal ?
                    -1 :
                    1
                );
            return self.sortOrder() * spaceship;
        };
        self.contributors.sort(comparator);
    };

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
        self.init();
    };

    self.submit = function() {
        self.messages([]);
        self.forceSubmit(true);
        bootbox.confirm({
            title: 'Save changes?',
            message: 'Are you sure you want to save these changes?',
            callback: function(result) {
                if (result) {
                    $osf.postJSON(
                        nodeApiUrl + 'contributors/manage/',
                        {contributors: self.serialize()}
                    ).done(function(response) {
                        // TODO: Don't reload the page here; instead use code below
                        if (response.redirectUrl) {
                            window.location.href = response.redirectUrl;
                        } else {
                            window.location.reload();
                        }
                    }).fail(function(xhr) {
                        self.init();
                        var response = xhr.responseJSON;
                        self.messages.push(
                            new MessageModel(
                                'Submission failed: ' + response.message_long,
                                'error'
                            )
                        );
                        self.forceSubmit(false);
                    });
                }
            }
        });
    };

};

////////////////
// Public API //
////////////////

function ContribManager(selector, contributors, adminContributors, user, isRegistration) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.contributors = contributors;
    self.adminContributors = adminContributors;
    self.viewModel = new ContributorsViewModel(contributors, adminContributors, user, isRegistration);
    self.init();
}

ContribManager.prototype.init = function() {
    ko.applyBindings(this.viewModel, this.$element[0]);
    this.$element.show();
};

module.exports = ContribManager;
