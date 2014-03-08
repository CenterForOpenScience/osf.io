this.Manage = (function(window, $, ko, bootbox) {

    var contribsEqual = function(a, b) {
        return a.id === b.id && a.permission === b.permission;
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
        },
        contributions: {
            label: 'Contributions',
            order: -1,
            func: function(item) {
                return item.contributions;
            }
        }
    };

    var ContributorModel = function(contributor) {

        var self = this;

        $.extend(self, contributor);
        self.permission = ko.observable(contributor.permission);

        self.serialize = function() {
            return ko.toJS(self);
        };

    };

    var ContributorsViewModel = function(contributors) {

        var self = this;
        self.original = ko.observableArray(contributors);

        self.contributors = ko.observableArray();

        self.messageText = ko.observable('');
        self.messageType = ko.observable('');
        self.messageClass = ko.computed(function() {
            return self.messageType() === 'success' ? 'text-success' : 'text-danger';
        });

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
            var admins = ko.utils.arrayFilter(self.contributors(), function(item) {
                return item.permission() === 'admin';
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
                self.messageText('Must have at least one admin contributor');
                self.messageType('error');
            } else {
                self.messageText('');
            }
        });

        self.init = function() {
            self.messageText('');
            self.contributors(self.original().map(function(item) {
                return new ContributorModel(item);
            }));
        };

        self.initListeners = function() {
            var self = this;
            $(window).on('beforeunload', function() {
                if (self.changed()) {
                    return 'There are unsaved changes to your contributor '
                        'settings. Are you sure you want to leave this page?'
                }
            });
        };

        self.init();
        self.initListeners();

        self.setupEditable = function(elm, data) {
            var $elm = $(elm);
            var $editable = $elm.find('.permission-editable');
            $editable.editable({
                showbuttons: false,
                value: data.permission(),
                source: [
                    {value: 'read', text: 'Read'},
                    {value: 'write', text: 'Write'},
                    {value: 'admin', text: 'Admin'}
                ],
                success: function(response, value) {
                    data.permission(value);
                }
            });
        };

        self.remove = function(data) {
            self.contributors.splice(
                self.contributors.indexOf(data), 1
            );
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
            return self.contributors().map(function(item) {
                return item.serialize();
            });
        };

        self.cancel = function() {
            self.init();
        };

        self.submit = function() {
            self.messageText('');
            bootbox.confirm('Are you sure you want to save these changes?', function(result) {
                if (result) {
                    $.osf.postJSON(
                        nodeApiUrl + 'contributors/manage/',
                        {contributors: self.serialize()},
                        function() {
                            self.original(ko.utils.arrayMap(self.contributors(), function(item) {
                                return item.serialize();
                            }));
                            self.messageText('Submission successful');
                            self.messageType('success');
                        }
                    ).fail(function(xhr) {
                        self.init();
                        var response = JSON.parse(xhr.responseText);
                        self.messageText('Submission failed: ' + response.message_long);
                        self.messageType('error');
                    });
                }
            });
        };

    };

    return {
        ViewModel: ContributorsViewModel
    }

})(window, $, ko, bootbox);
