/**
 * Controller for the Add Contributor modal.
 */
(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout', 'bootstrap', 'editable'], factory);
    } else {
        global.ContribAdder = factory(jQuery, global.ko);
    }
}(this, function($, ko) {

    NODE_OFFSET = 25;
    // Max number of recent/common contributors to show
    var MAX_RECENT = 5;

    /**
     * The add contributor VM, scoped to the add contributor modal dialog.
     */
    var AddContributorViewModel = function(title, parentId, parentTitle) {

        var self = this;

        self.permissions = ['read', 'write', 'admin'];

        self.title = title;
        self.parentId = parentId;
        self.parentTitle = parentTitle;

        self.page = ko.observable('whom');
        self.pageTitle = ko.computed(function() {
            return {
                whom: 'Add Contributors',
                which: 'Select Components',
                invite: 'Add Unregistered Contributor'
            }[self.page()];
        });
        self.query = ko.observable();
        self.results = ko.observableArray([]);
        self.selection = ko.observableArray();
        self.notification = ko.observable('');
        self.inviteError = ko.observable('');
        self.numberOfPages = ko.observable(0);
        self.currentPage = ko.observable(0);

        self.paginators = ko.observableArray([]);
        self.nodes = ko.observableArray([]);
        self.nodesToChange = ko.observableArray();
        $.getJSON(
            nodeApiUrl + 'get_editable_children/',
            {},
            function(result) {
                $.each(result.children || [], function(idx, child) {
                    child.margin = NODE_OFFSET + child.indent * NODE_OFFSET + 'px';
                });
                self.nodes(result.children);
            }
        );

        self.foundResults = ko.computed(function() {
            return self.query() && self.results().length;
        });

        self.noResults = ko.computed(function() {
            return self.query() && !self.results().length;
        });

        self.inviteName = ko.observable();
        self.inviteEmail = ko.observable();

        self.selectWhom = function() {
            self.page('whom');
        };
        self.selectWhich = function() {
            self.page('which');
        };

        self.gotoInvite = function() {
            self.inviteName(self.query());
            self.inviteError('');
            self.inviteEmail('');
            self.page('invite');
        };

        self.goToPage = function(page) {
            self.page(page);
        };

        /**
         * A simple Contributor model that receives data from the
         * contributor search endpoint. Adds an addiitonal displayProjectsinCommon
         * attribute which is the human-readable display of the number of projects the
         * currently logged-in user has in common with the contributor.
         */
        function Contributor(data) {
            $.extend(this, data);
            if (data.n_projects_in_common === 1) {
                this.displayProjectsInCommon = data.n_projects_in_common + ' project in common';
            } else if (data.n_projects_in_common !== 0) {
                this.displayProjectsInCommon = data.n_projects_in_common + ' projects in common';
            } else {
                this.displayProjectsInCommon = '';
            }
        }

        self.startSearch = function() {
            self.currentPage(0);
            self.search();
        };

        self.search = function() {
            self.notification(false);
            if (self.query()) {
                $.getJSON(
                    '/api/v1/user/search/',
                    {
                        query: self.query(),
                        excludeNode: nodeId,
                        page: self.currentPage
                    },
                    function(result) {
                        var contributors = result.users.map(function(userData) {
                            return new Contributor(userData);
                        });
                        self.results(contributors);
                        self.currentPage(result.page);
                        self.numberOfPages(result.pages);
                        self.addNewPaginators();
                    }
                );
            } else {
                self.results([]);
                self.currentPage(0);
                self.totalPages(0);
            }
        };

        var MAX_PAGES_ON_PAGINATOR = 7;
        var MAX_PAGES_ON_PAGINATOR_SIDE = 5;

        self.addNewPaginators = function() {
            self.paginators.removeAll();
            if (self.numberOfPages() > 1) {
                self.paginators.push({
                    style: (self.currentPage() === 0)? 'disabled' : '',
                    handler: self.previousPage,
                    text: '&lt;'
                });
                self.paginators.push({
                    style: (self.currentPage() === 0)? 'active' : '',
                    text: '1',
                    handler: function () {
                        self.currentPage(0);
                        self.search();
                    }
                });
                if (self.numberOfPages() <= MAX_PAGES_ON_PAGINATOR) {
                    for (var i = 1; i < self.numberOfPages() - 1; i++) {
                        self.paginators.push({
                            style: (self.currentPage() === i)? 'active' : '',
                            text: i + 1,
                            handler: function () {
                                self.currentPage(parseInt(this.text) - 1);
                                self.search();
                            }
                        });
                    }
                } else if (self.currentPage() < MAX_PAGES_ON_PAGINATOR_SIDE - 1) { // One ellipse at the end
                    for (var i = 1; i < MAX_PAGES_ON_PAGINATOR_SIDE; i++) {
                        self.paginators.push({
                            style: (self.currentPage() === i)? 'active' : '',
                            text: i + 1,
                            handler: function () {
                                self.currentPage(parseInt(this.text) - 1);
                                self.search();
                            }
                        });
                    }
                    self.paginators.push({
                        style: 'disabled',
                        text: '...',
                        handler: function () {}
                    });
                } else if (self.currentPage() > self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE) { // one ellipses at the beginning
                    self.paginators.push({
                        style: 'disabled',
                        text: '...',
                        handler: function () {}
                    });
                    for (var i = self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE; i < self.numberOfPages() - 1; i++) {
                        self.paginators.push({
                            style: (self.currentPage() === i)? 'active' : '',
                            text: i + 1,
                            handler: function () {
                                self.currentPage(parseInt(this.text) - 1);
                                self.search();
                            }
                        });
                    }
                } else { // two ellipses
                    self.paginators.push({
                        style: 'disabled',
                        text: '...',
                        handler: function () {}
                    });
                    for (var i = self.currentPage() - 1; i <= self.currentPage() + 1; i++) {
                        self.paginators.push({
                            style: (self.currentPage() === i)? 'active' : '',
                            text: i + 1,
                            handler: function () {
                                self.currentPage(parseInt(this.text) - 1);
                                self.search();
                            }
                        });
                    }
                    self.paginators.push({
                        style: 'disabled',
                        text: '...',
                        handler: function () {}
                    });
                }
                self.paginators.push({
                    style: (self.currentPage() === self.numberOfPages() - 1)? 'active' : '',
                    text: self.numberOfPages(),
                    handler: function () {
                        self.currentPage(self.numberOfPages() - 1);
                        self.search();
                    }
                });
                self.paginators.push({
                    style: (self.currentPage() === self.numberOfPages() - 1)? 'disabled' : '',
                    handler: self.nextPage,
                    text: '&gt;'
                });
            }
        };

        self.nextPage = function() {
            self.currentPage(self.currentPage() + 1);
            self.search();
        };

        self.previousPage = function() {
            self.currentPage(self.currentPage() - 1);
            self.search();
        };

        self.importFromParent = function() {
            self.notification(false);
            $.getJSON(
                nodeApiUrl + 'get_contributors_from_parent/',
                {},
                function(result) {
                    if (!result.contributors.length) {
                        self.notification({
                            'message': 'All contributors from parent already included.',
                            'level': 'info'
                        });
                    }
                    self.results(result.contributors);
                }
            );
        };

        self.recentlyAdded = function() {
            self.notification(false);
            var url = nodeApiUrl + 'get_recently_added_contributors/?max=' + MAX_RECENT.toString();
            $.getJSON(
                url,
                {},
                function(result) {
                    if (!result.contributors.length) {
                        self.notification({
                            'message': 'All recent collaborators already included.',
                            'level': 'info'
                        });
                    }
                    var contribs = [];
                    var numToDisplay = result.contributors.length;
                    for (var i=0; i< numToDisplay; i++) {
                        contribs.push(new Contributor(result.contributors[i]));
                    }
                    self.results(contribs);
                    self.numberOfPages(1);
                }
            ).fail(function (xhr, textStatus, error) {
                self.notification({
                    'message':
                        'OSF was unable to resolve your request. If this issue persists, ' +
                        'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.',
                    'level': 'warning'
                });
                Raven.captureMessage('Could not GET recentlyAdded contributors.', {
                    url: url,
                    textStatus: textStatus,
                    error: error
                });
            });
        };

        self.mostInCommon = function() {
            self.notification(false);
            var url = nodeApiUrl + 'get_most_in_common_contributors/?max=' + MAX_RECENT.toString();
            $.getJSON(
                url,
                {},
                function(result) {
                    if (!result.contributors.length) {
                        self.notification({
                            'message': 'All frequent collaborators already included.',
                            'level': 'info'
                        });
                    }
                    var contribs = [];
                    var numToDisplay = result.contributors.length;
                    for (var i=0; i< numToDisplay; i++) {
                        contribs.push(new Contributor(result.contributors[i]));
                    }
                    self.results(contribs);
                    self.numberOfPages(1);
                }
            ).fail(function (xhr, textStatus, error) {
                self.notification({
                    'message':
                        'OSF was unable to resolve your request. If this issue persists, ' +
                        'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.',
                    'level': 'warning'
                });
                Raven.captureMessage('Could not GET mostInCommon contributors.', {
                    url: url,
                    textStatus: textStatus,
                    error: error
                });
            });
        };

        self.addTips = function(elements) {
            elements.forEach(function(element) {
                $(element).find('.contrib-button').tooltip();
            });
        };

        self.setupEditable = function(elm, data) {
            var $elm = $(elm);
            var $editable = $elm.find('.permission-editable');
            $editable.editable({
                showbuttons: false,
                value: 'admin',
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

        self.afterRender = function(elm, data) {
            self.addTips(elm, data);
            self.setupEditable(elm, data);
        };

        function postInviteRequest(fullname, email) {
            $.osf.postJSON(
                nodeApiUrl + 'invite_contributor/',
                {'fullname': fullname, 'email': email}
            ).done(
                onInviteSuccess
            ).fail(
                onInviteError
            );
        }

        function onInviteSuccess(result) {
            self.query('');
            self.results([]);
            self.page('whom');
            self.add(result.contributor);
        }

        function onInviteError(xhr) {
            var response = JSON.parse(xhr.responseText);
            // Update error message
            self.inviteError(response.message);
        }

        /** Validate the invite form. Returns a string error message or
        *   true if validation succeeds.
        */
        self.validateInviteForm = function (){
            // Make sure Full Name is not blank
            if (!self.inviteName().trim().length) {
                return 'Full Name is required.';
            }
            if (self.inviteEmail() && !$.osf.isEmail(self.inviteEmail())) {
                return 'Not a valid email address.';
            }
            // Make sure that entered email is not already in selection
            for (var i=0, contrib; contrib = self.selection()[i]; ++i){
                var contribEmail = contrib.email.toLowerCase().trim();
                if (contribEmail === self.inviteEmail().toLowerCase().trim()) {
                    return self.inviteEmail() + ' is already in queue.';
                }
            }
            return true;
        };

        self.postInvite = function() {
            self.inviteError('');
            var validated = self.validateInviteForm();
            if (typeof validated === 'string') {
                self.inviteError(validated);
                return false;
            }
            return postInviteRequest(self.inviteName(), self.inviteEmail());
        };

        self.add = function(data) {
            data.permission = ko.observable('admin');
            // All manually added contributors are visible
            data.visible = true;
            self.selection.push(data);
            // Hack: Hide and refresh tooltips
            $('.tooltip').hide();
            $('.contrib-button').tooltip();
        };


        self.remove = function(data) {
            self.selection.splice(
                self.selection.indexOf(data), 1
            );
            // Hack: Hide and refresh tooltips
            $('.tooltip').hide();
            $('.contrib-button').tooltip();
        };

        self.addAll = function() {
            $.each(self.results(), function(idx, result) {
                if (self.selection().indexOf(result) === -1) {
                    self.add(result);
                }
            });
        };

        self.removeAll = function() {
            $.each(self.selection(), function(idx, selected) {
                self.remove(selected);
            });
        };

        self.cantSelectNodes = function() {
            return self.nodesToChange().length === self.nodes().length;
        };
        self.cantDeselectNodes = function() {
            return self.nodesToChange().length === 0;
        };

        self.selectNodes = function() {
            self.nodesToChange($.osf.mapByProperty(self.nodes(), 'id'));
        };
        self.deselectNodes = function() {
            self.nodesToChange([]);
        };

        self.selected = function(data) {
            for (var idx=0; idx < self.selection().length; idx++) {
                if (data.id === self.selection()[idx].id){
                    return true;
                }
            }
            return false;
        };


        self.addingSummary = ko.computed(function() {
            var names = $.map(self.selection(), function(result) {
                return result.fullname;
            });
            return names.join(', ');
        });

        self.submit = function() {
            $.osf.block();
            $('.modal').modal('hide');
            $.osf.postJSON(
                nodeApiUrl + 'contributors/',
                {
                    users: self.selection().map(function(user) {
                        return ko.toJS(user);
                    }),
                    node_ids: self.nodesToChange()
                }
            ).done(function() {
                window.location.reload();
            }).fail(function() {
                $.osf.unblock();
                $.osf.growl('Error','Add contributor failed.');
            });
        };

        self.clear = function() {
            self.page('whom');
            self.query('');
            self.results([]);
            self.selection([]);
            self.nodesToChange([]);
            self.notification(false);
        };

    };

    ////////////////
    // Public API //
    ////////////////

    function ContribAdder (selector, nodeTitle, nodeId, parentTitle) {
        var self = this;
        self.selector = selector;
        self.$element = $(selector);
        self.nodeTitle = nodeTitle;
        self.nodeId = nodeId;
        self.parentTitle = parentTitle;
        self.viewModel = new AddContributorViewModel(self.nodeTitle,
            self.nodeId, self.parentTitle);
        self.init();
    }

    ContribAdder.prototype.init = function() {
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
        // Load recently added contributors every time the modal is activated.
        self.$element.on('shown.bs.modal', function() {
            self.viewModel.recentlyAdded();
        });
    };

    return ContribAdder;
}));
