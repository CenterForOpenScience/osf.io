/**
 * Controller for the Add Contributor modal.
 */
'use strict';

require('css/add-contributors.css');

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');  // TODO: Why is this required? Is it? See [#OSF-6100]
var Raven = require('raven-js');

var oop = require('js/oop');
var $osf = require('js/osfHelpers');
var osfLanguage = require('js/osfLanguage');
var Paginator = require('js/paginator');
var NodeSelectTreebeard = require('js/nodeSelectTreebeard');
var m = require('mithril');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');


function Contributor(data) {
    $.extend(this, data);
    if (data.n_projects_in_common === 1) {
        this.displayProjectsInCommon = data.n_projects_in_common + ' project in common';
    } else if (data.n_projects_in_common === -1) {
        this.displayProjectsInCommon = 'Yourself';
    } else if (data.n_projects_in_common !== 0) {
        this.displayProjectsInCommon = data.n_projects_in_common + ' projects in common';
    } else {
        this.displayProjectsInCommon = '';
    }
}

var AddContributorViewModel;
AddContributorViewModel = oop.extend(Paginator, {
    constructor: function (title, nodeId, parentId, parentTitle, options) {
        this.super.constructor.call(this);
        var self = this;

        self.title = title;
        self.nodeId = nodeId;
        self.nodeApiUrl = '/api/v1/project/' + self.nodeId + '/';
        self.parentId = parentId;
        self.parentTitle = parentTitle;
        self.async = options.async || false;
        self.callback = options.callback || function () {
            };
        self.nodesOriginal = {};
        //state of current nodes
        self.childrenToChange = ko.observableArray();
        self.nodesState = ko.observable();
        //nodesState is passed to nodesSelectTreebeard which can update it and key off needed action.
        self.nodesState.subscribe(function (newValue) {
            //The subscribe causes treebeard changes to change which nodes will be affected
            var childrenToChange = [];
            for (var key in newValue) {
                newValue[key].changed = newValue[key].checked !== self.nodesOriginal[key].checked;
                if (newValue[key].changed && key !== self.nodeId) {
                    childrenToChange.push(key);
                }
            }
            self.childrenToChange(childrenToChange);
            m.redraw(true);
        });

        //list of permission objects for select.
        self.permissionList = [
            {value: 'read', text: 'Read'},
            {value: 'write', text: 'Read + Write'},
            {value: 'admin', text: 'Administrator'}
        ];

        self.page = ko.observable('whom');
        self.pageTitle = ko.computed(function () {
            return {
                whom: 'Add Contributors',
                which: 'Select Components',
                invite: 'Add Unregistered Contributor'
            }[self.page()];
        });
        self.query = ko.observable();
        self.results = ko.observableArray([]);
        self.contributors = ko.observableArray([]);
        self.inviteLinks = ko.observableArray([]);
        self.selection = ko.observableArray();

        self.contributorIDsToAdd = ko.pureComputed(function () {
            return self.selection().map(function (user) {
                return user.id;
            });
        });

        self.notification = ko.observable('');
        self.inviteError = ko.observable('');
        self.doneSearching = ko.observable(false);
        self.totalPages = ko.observable(0);
        self.childrenToChange = ko.observableArray();

        self.foundResults = ko.pureComputed(function () {
            return self.query() && self.results().length;
        });

        self.noResults = ko.pureComputed(function () {
            return self.query() && !self.results().length && self.doneSearching();
        });

        self.showLoading = ko.pureComputed(function () {
            return !self.doneSearching() && !!self.query();
        });

        self.addAllVisible = ko.pureComputed(function () {
            var selected_ids = self.selection().map(function (user) {
                return user.id;
            });
            var contributors = self.contributors();
            return ($osf.any(
                $.map(self.results(), function (result) {
                    return contributors.indexOf(result.id) === -1 && selected_ids.indexOf(result.id) === -1;
                })
            ));
        });

        self.removeAllVisible = ko.pureComputed(function () {
            return self.selection().length > 0;
        });

        self.inviteName = ko.observable();
        self.inviteEmail = ko.observable();

        self.addingSummary = ko.computed(function () {
            var names = $.map(self.selection(), function (result) {
                return result.fullname;
            });
            return names.join(', ');
        });
    },
    hide: function () {
        $('.modal').modal('hide');
    },
    selectWhom: function () {
        this.page('whom');
    },
    selectWhich: function () {
        //when the next button is hit by the user, the nodes to change and disable are decided
        var self = this;
        var nodesState = self.nodesState();
        for (var key in nodesState) {
            var i;
            var node = nodesState[key];
            var enabled = nodesState[key].isAdmin;
            var checked = nodesState[key].checked;
            if (enabled) {
                var nodeContributors = [];
                for (i = 0; i < node.contributors.length; i++) {
                    nodeContributors.push(node.contributors[i].id);
                }
                for (i = 0; i < self.contributorIDsToAdd().length; i++) {
                    if (nodeContributors.indexOf(self.contributorIDsToAdd()[i]) < 0) {
                        enabled = true;
                        break;
                    }
                    else {
                        checked = true;
                        enabled = false;
                    }
                }
            }
            nodesState[key].enabled = enabled;
            nodesState[key].checked = checked;
        }
        self.nodesState(nodesState);
        this.page('which');
    },
    gotoInvite: function () {
        var self = this;
        self.inviteName(self.query());
        self.inviteError('');
        self.inviteEmail('');
        self.page('invite');
    },
    goToPage: function (page) {
        this.page(page);
    },
    /**
     * A simple Contributor model that receives data from the
     * contributor search endpoint. Adds an additional displayProjectsinCommon
     * attribute which is the human-readable display of the number of projects the
     * currently logged-in user has in common with the contributor.
     */
    startSearch: function () {
        this.pageToGet(0);
        this.fetchResults();
    },
    fetchResults: function () {
        var self = this;
        self.doneSearching(false);
        self.notification(false);
        if (self.query()) {
            return $.getJSON(
                '/api/v1/user/search/', {
                    query: self.query(),
                    page: self.pageToGet
                },
                function (result) {
                    var contributors = result.users.map(function (userData) {
                        userData.added = (self.contributors().indexOf(userData.id) !== -1);
                        return new Contributor(userData);
                    });
                    self.doneSearching(true);
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
            self.doneSearching(true);
        }
    },
    getInviteLinks: function () {
        var self = this;
        var url = self.nodeApiUrl + 'private_link/';

        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {

            response.node.private_links = response.node.private_links.map(function (privateLink) {
                privateLink.date_created = new $osf.FormattableDate(privateLink.date_created);
                privateLink.url = response.node.absolute_url + '?view_only=' +  privateLink.key;

                privateLink.components = privateLink.nodes.map(function(component){
                    return component.title;
                }).join(', ');

                return privateLink;
            });

            self.inviteLinks(response.node);

            }).fail(
        );

    },
    getContributors: function () {
        var self = this;
        self.notification(false);
        var url = $osf.apiV2Url('nodes/' + window.contextVars.node.id + '/contributors/');

        return $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json',
            contentType: 'application/vnd.api+json;',
            crossOrigin: true,
            xhrFields: {withCredentials: true},
            processData: false
        }).done(function (response) {
            var contributors = response.data.map(function (user) {
                return user.id;
            });
            self.contributors(contributors);
        });
    },
    importFromParent: function () {
        var self = this;
        self.notification(false);
        $.getJSON(
            self.nodeApiUrl + 'get_contributors_from_parent/', {},
            function (result) {
                var contributors = result.contributors.map(function (user) {
                    var added = (self.contributors().indexOf(user.id) !== -1);
                    var updatedUser = $.extend({}, user, {added: added});
                    return updatedUser;
                });
                self.results(contributors);
                self.doneSearching(true);
            }
        );
    },
    addTips: function (elements) {
        elements.forEach(function (element) {
            $(element).find('.contrib-button').tooltip();
        });
    },
    afterRender: function (elm, data) {
        var self = this;
        self.addTips(elm, data);
    },
    makeAfterRender: function () {
        var self = this;
        return function (elm, data) {
            return self.afterRender(elm, data);
        };
    },
    /** Validate the invite form. Returns a string error message or
     *   true if validation succeeds.
     */
    validateInviteForm: function () {
        var self = this;
        // Make sure Full Name is not blank
        if (!self.inviteName().trim().length) {
            return 'Full Name is required.';
        }
        if (self.inviteEmail() && !$osf.isEmail(self.inviteEmail())) {
            return 'Not a valid email address.';
        }
        // Make sure that entered email is not already in selection
        for (var i = 0, contrib; contrib = self.selection()[i]; ++i) {
            if (contrib.email) {
                var contribEmail = contrib.email.toLowerCase().trim();
                if (contribEmail === self.inviteEmail().toLowerCase().trim()) {
                    return self.inviteEmail() + ' is already in queue.';
                }
            }
        }
        return true;
    },
    postInvite: function () {
        var self = this;
        self.inviteError('');
        var validated = self.validateInviteForm();
        if (typeof validated === 'string') {
            self.inviteError(validated);
            return false;
        }
        return self.postValidateInvite(self.inviteName(), self.inviteEmail());
    },
    add: function (data) {
        var self = this;
        data.permission = ko.observable(self.permissionList[1]); //default permission write
        // All manually added contributors are visible
        data.visible = true;
        this.selection.push(data);
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    },
    remove: function (data) {
        this.selection.splice(
            this.selection.indexOf(data), 1
        );
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    },
    addAll: function () {
        var self = this;
        var selected_ids = self.selection().map(function (user) {
            return user.id;
        });
        $.each(self.results(), function (idx, result) {
            if (selected_ids.indexOf(result.id) === -1 && self.contributors().indexOf(result.id) === -1) {
                self.add(result);
            }
        });
    },
    removeAll: function () {
        var self = this;
        $.each(self.selection(), function (idx, selected) {
            self.remove(selected);
        });
    },
    selected: function (data) {
        var self = this;
        for (var idx = 0; idx < self.selection().length; idx++) {
            if (data.id === self.selection()[idx].id) {
                return true;
            }
        }
        return false;
    },
    selectAllNodes: function () {
        //select all nodes to add a contributor to.  THe changed variable is set here for timing between
        // treebeard and knockout
        var self = this;
        var nodesState = ko.toJS(self.nodesState());
        for (var key in nodesState) {
            if (nodesState[key].enabled) {
                nodesState[key].checked = true;
            }
        }
        self.nodesState(nodesState);
    },
    selectNoNodes: function () {
        //select no nodes to add a contributor to.  THe changed variable is set here for timing between
        // treebeard and knockout
        var self = this;
        var nodesState = ko.toJS(self.nodesState());
        for (var key in nodesState) {
            if (nodesState[key].enabled && nodesState[key].checked) {
                nodesState[key].checked = false;
            }
        }
        self.nodesState(nodesState);
    },
    submit: function () {
        var self = this;
        $osf.block();
        var url = self.nodeApiUrl + 'contributors/';
        return $osf.postJSON(
            url, {
                users: ko.utils.arrayMap(self.selection(), function (user) {
                    var permission = user.permission().value; //removes the value from the object
                    var tUser = JSON.parse(ko.toJSON(user)); //The serialized user minus functions
                    tUser.permission = permission; //shoving the permission value into permission
                    return tUser; //user with simplified permissions
                }),
                node_ids: self.childrenToChange()
            }
        ).done(function (response) {
            if (self.async) {
                self.contributors($.map(response.contributors, function (contrib) {
                    return contrib.id;
                }));
                self.hide();
                $osf.unblock();
                if (self.callback) {
                    self.callback(response);
                }
            } else {
                window.location.reload();
            }
        }).fail(function (xhr, status, error) {
            self.hide();
            $osf.unblock();
            $osf.growl('Could not add contributors', 'There was a problem trying to add contributors. ' + osfLanguage.REFRESH_OR_SUPPORT);
            Raven.captureMessage('Error adding contributors', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    },
    clear: function () {
        var self = this;
        self.page('whom');
        self.query('');
        self.results([]);
        self.selection([]);
        self.childrenToChange([]);
        self.notification(false);
    },
    postValidateInvite: function (fullname, email) {
        var self = this;
        return $osf.postJSON(
            self.nodeApiUrl + 'invite_contributor/', {
                'fullname': fullname,
                'email': email
            }
        ).done(
            self.onInviteSuccess.bind(self)
        ).fail(
            self.onInviteError.bind(self)
        );
    },
    onInviteSuccess: function (result) {
        var self = this;
        result.contributor.inviteLink = $('input:radio[name ="inviteLinkRadioGroup"]:checked').val();
        self.query('');
        self.results([]);
        self.page('whom');
        self.add(result.contributor);
    },
    onInviteError: function (xhr) {
        var response = JSON.parse(xhr.responseText);
        // Update error message
        this.inviteError(response.message);
    },
    hasChildren: function() {
        var self = this;
        return (Object.keys(self.nodesOriginal).length > 1);
    },
    /**
     * get node tree for treebeard from API V1
     */
    fetchNodeTree: function (treebeardUrl) {
        var self = this;
        return $.ajax({
            url: treebeardUrl,
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
            self.nodesOriginal = projectSettingsTreebeardBase.getNodesOriginal(response[0], self.nodesOriginal);
            var nodesState = $.extend(true, {}, self.nodesOriginal);
            var nodeParent = response[0].node.id;
            //parent node is changed by default
            nodesState[nodeParent].checked = true;
            //parent node cannot be changed
            nodesState[nodeParent].isAdmin = false;
            self.nodesState(nodesState);
        }).fail(function (xhr, status, error) {
            $osf.growl('Error', 'Unable to retrieve project settings');
            Raven.captureMessage('Could not GET project settings.', {
                url: treebeardUrl, status: status, error: error
            });
        });
    }
});


////////////////
// Public API //
////////////////

function ContribAdder(selector, nodeTitle, nodeId, parentId, parentTitle, options) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.nodeTitle = nodeTitle;
    self.nodeId = nodeId;
    self.parentId = parentId;
    self.parentTitle = parentTitle;
    self.options = options || {};
    self.viewModel = new AddContributorViewModel(
        self.nodeTitle,
        self.nodeId,
        self.parentId,
        self.parentTitle,
        self.options
    );
    self.init();
}

ContribAdder.prototype.init = function() {
    var self = this;
    var treebeardUrl = window.contextVars.node.urls.api + 'tree/';
    self.viewModel.getContributors();
    self.viewModel.getInviteLinks();
    self.viewModel.fetchNodeTree(treebeardUrl).done(function(response) {
        new NodeSelectTreebeard('addContributorsTreebeard', response, self.viewModel.nodesState);
    });
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

module.exports = ContribAdder;
