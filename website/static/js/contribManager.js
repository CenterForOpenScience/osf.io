(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout', 'jquery-ui',
                'vendor/jquery-blockui/jquery.blockui',
                'vendor/knockout-sortable/knockout-sortable',
                'osfutils'], factory);
    } else {
        global.ContribManager = factory(jQuery, global.ko);
    }
}(this, function($, ko) {

    var contribsEqual = function(a, b) {
        return a.id === b.id && a.permission === b.permission &&
            a.deleteStaged === b.deleteStaged;
    };

    // Modified from http://stackoverflow.com/questions/7837456/comparing-two-arrays-in-javascript
    var arraysEqual = function(a, b) {
        var i = a.length;
        if (i != b.length) return false;
        while (i--) {
            if (!contribsEqual(a[i], b[i])) return false;
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

    var setupEditable = function(elm, data) {
        var $elm = $(elm);
        var $editable = $elm.find('.permission-editable');
        $editable.editable({
            showbuttons: false,
            value: data.permission(),
            source: [
                {value: 'read', text: 'Read'},
                {value: 'write', text: 'Read + Write'},
                {value: 'admin', text: 'Administrator'}
            ],
            success: function(response, value) {
                data.permission(value);
            }
        });
    };

    var ContributorModel = function(contributor, pageOwner, isRegistration) {

        var self = this;

        $.extend(self, contributor);
        self.permission = ko.observable(contributor.permission);
        self.deleteStaged = ko.observable(contributor.deleteStaged);

        self.pageOwner = pageOwner;
        self.serialize = function() {
            return ko.toJS(self);
        };

        self.remove = function() {
            self.deleteStaged(true);
        };
        self.unremove = function(data, event) {
            $target = $(event.target);
            if (!$target.hasClass('contrib-button')) {
                self.deleteStaged(false);
            }
        };

        self.notDeleteStaged = ko.computed(function() {
            return !self.deleteStaged();
        });
        self.formatPermission = ko.computed(function() {
            var permission = self.permission();
            return permission.charAt(0).toUpperCase() + permission.slice(1);
        });

        self.canRemove = ko.computed(function(){
            return (self.id === pageOwner['id']) && !isRegistration;
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
            $.osf.postJSON(
                nodeApiUrl + 'beforeremovecontributors/',
                payload,
                function(response) {

                    var prompt = $.osf.joinPrompts(response.prompts, 'Remove <strong>' + name + '</strong> from contributor list?');
                    bootbox.confirm({
                        title: 'Delete Contributor?',
                        message: prompt,
                        callback: function(result) {
                            if (result) {
                                $.osf.postJSON(
                                    nodeApiUrl + 'removecontributors/',
                                    payload,
                                    function(response) {

                                        if (response.redirectUrl) {
                                            window.location.href = response.redirectUrl;
                                        } else {
                                            window.location.reload();
                                        }
                                    }
                                ).fail(function(xhr) {
                                    var response = JSON.parse(xhr.responseText);
                                    bootbox.alert('Error: ' + response.message_long);
                                });
                            }
                        }
                    });
                }
            );
            return false;
        };

    };

    var ContributorsViewModel = function(contributors, user, isRegistration) {

        var self = this;
        for (var i=0; i<contributors.length; i++) {
            contributors[i].deleteStaged = false;
        }
        self.original = ko.observableArray(contributors);

        self.contributors = ko.observableArray();

        self.user = ko.observable(user);
        self.userIsAdmin  = ko.observable($.inArray('admin', user.permissions) !== -1);
        self.canEdit = ko.computed(function() {
            return (self.userIsAdmin()) && !isRegistration;
        });

        self.messageText = ko.observable('');
        self.messageType = ko.observable('');
        self.messageClass = ko.computed(function() {
            return self.messageType() === 'success' ? 'text-success' : 'text-danger';
        });

        // Hack: Ignore beforeunload when submitting
        // TODO: Single-page-ify and remove this
        self.forceSubmit = ko.observable(false);

        self.sortKeys = Object.keys(sortMap);
        self.sortKey = ko.observable(self.sortKeys[0]);
        self.sortOrder = ko.observable(0);
        self.sortClass = ko.computed(function() {
            if (self.sortOrder() == 1) {
                return 'icon-caret-up';
            } else if (self.sortOrder() == -1) {
                return 'icon-caret-down';
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
        self.valid = ko.computed(function() {
            var contributors = ko.utils.arrayFilter(self.contributors(), function(item) {
                return !item.deleteStaged();
            });
            var admins = ko.utils.arrayFilter(contributors, function(item) {
                return item.permission() === 'admin' &&
                    item.registered;
            });
            return !!admins.length;
        });
        self.canSubmit = ko.computed(function() {
            return self.changed() && self.valid();
        });
        self.changed.subscribe(function() {
            self.messageText('');
        });
        self.valid.subscribe(function(value) {
            if (!value) {
                self.messageText('Must have at least one registered admin contributor');
                self.messageType('error');
            } else {
                self.messageText('');
            }
        });

        self.init = function() {
            self.messageText('');
            self.contributors(self.original().map(function(item) {
                return new ContributorModel(item, self.user(), isRegistration);
            }));
        };

        self.initListeners = function() {
            var self = this;
            // Warn on add contributors if pending changes
            $('[href="#addContributors"]').on('click', function() {
                if (self.changed()) {
                    bootbox.alert(
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
                    return 'There are unsaved changes to your contributor '
                        'settings. Are you sure you want to leave this page?'
                }
            });
        };

        self.init();
        self.initListeners();

        self.setupEditable = function(elm, data) {
            setupEditable(elm, data);
        };

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
            toSubmit = ko.utils.arrayFilter(self.contributors(), function(item) {
                return !item.deleteStaged();
            });
            return ko.utils.arrayMap(toSubmit, function(item) {
                return item.serialize();
            });
        };

        self.cancel = function() {
            self.init();
        };

        self.submit = function() {
            self.messageText('');
            self.forceSubmit(true);
            bootbox.confirm('Are you sure you want to save these changes?', function(result) {
                if (result) {
                    $.osf.postJSON(
                        nodeApiUrl + 'contributors/manage/',
                        {contributors: self.serialize()},
                        function(response) {
                            // TODO: Don't reload the page here; instead use code below
                            if (response.redirectUrl) {
                                window.location.href = response.redirectUrl;
                            } else {
                                window.location.reload();
                            }
//                            self.contributors(ko.utils.arrayFilter(self.contributors(), function(item) {
//                                return !item.deleteStaged();
//                            }));
//                            self.original(ko.utils.arrayMap(self.contributors(), function(item) {
//                                return item.serialize();
//                            }));
//                            self.messageText('Submission successful');
//                            self.messageType('success');
                        }
                    ).fail(function(xhr) {
                        self.init();
                        var response = JSON.parse(xhr.responseText);
                        self.messageText('Submission failed: ' + response.message_long);
                        self.messageType('error');
                        self.forceSubmit(false);
                    });
                }
            });
        };

    };

    ////////////////
    // Public API //
    ////////////////

    function ContribManager(selector, contributors, user, isRegistration) {
        var self = this;
        self.selector = selector;
        self.$element = $(selector);
        self.contributors = contributors;
        self.viewModel = new ContributorsViewModel(contributors, user, isRegistration);
        self.init();
    }

    ContribManager.prototype.init = function() {
        ko.applyBindings(this.viewModel, this.$element[0]);
        this.$element.show();
    };

    return ContribManager;

}));
