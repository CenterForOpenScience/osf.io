this.Manage = (function($, ko, bootbox) {

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
        self.original = contributors;

        self.contributors = ko.observableArray();

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

        self.init = function() {
            self.contributors(self.original.map(function(item) {
                return new ContributorModel(item);
            }));
        };

        self.init();

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
            bootbox.confirm('Are you sure you want to remove ' + data.fullname + ' from this project?', function(result) {
                if (result) {
                    self.contributors.splice(
                        self.contributors.indexOf(data), 1
                    );
                }
            });
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
            bootbox.confirm('Are you sure you want to discard these changes?', function(result) {
                if (result) {
                    self.init();
                }
            });
        };

        self.submit = function() {
            bootbox.confirm('Are you sure you want to save these changes?', function(result) {
                if (result) {
                    $.osf.postJSON(
                        nodeApiUrl + 'contributors/manage/',
                        {contributors: self.serialize()},
                        function() {
                            window.location.reload();
                        }
                    );
                }
            });
        };

    };

    return {
        ViewModel: ContributorsViewModel
    }

})($, ko, bootbox);
