/**
 * Controller for the Add Contributor modal.
 */
'use strict';

require('css/add-contributors.css');

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var lodashGet = require('lodash.get');

var oop = require('js/oop');
var $osf = require('js/osfHelpers');
var osfLanguage = require('js/osfLanguage');
var Paginator = require('js/paginator');
var NodeSelectTreebeard = require('js/nodeSelectTreebeard');
var m = require('mithril');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');
var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

function Contributor(data) {
    $.extend(this, data);
    if (data.n_projects_in_common === 1) {
        this.displayProjectsInCommon = data.n_projects_in_common + _(' project in common');
    } else if (data.n_projects_in_common === -1) {
        this.displayProjectsInCommon = _('Yourself');
    } else if (data.n_projects_in_common !== 0) {
        this.displayProjectsInCommon = data.n_projects_in_common + _(' projects in common');
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
        self.canSubmit = ko.observable(true);
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
            {value: 'read', text: _('Read')},
            {value: 'write', text: _('Read + Write')},
            {value: 'admin', text: _('Administrator')}
        ];

        self.inviteFromExplicitLink = false;
        self.page = ko.observable('whom');
        self.pageTitle = ko.computed(function () {
            var flag = self.inviteFromExplicitLink;
            self.inviteFromExplicitLink = false;
            return {
                whom: _('Add Contributors'),
                which: _('Select Components'),
                invite: flag ?
                    _('Invite new contributor by e-mail') :
                    _('Add Unregistered Contributor')
            }[self.page()];
        });
        self.query = ko.observable();
        self.results = ko.observableArray([]);
        self.contributors = ko.observableArray([]);
        self.selection = ko.observableArray();

        self.contributorIDsToAdd = ko.pureComputed(function () {
            return self.selection().map(function (user) {
                return user.id;
            });
        });

        self.notification = ko.observable('');
        self.inviteError = ko.observable('');
        self.doneSearching = ko.observable(false);
        self.parentImport = ko.observable(false);
        self.totalPages = ko.observable(0);
        self.childrenToChange = ko.observableArray();

        self.emailSearch = ko.pureComputed(function () {
            var emailRegex = new RegExp('[^\\s]+@[^\\s]+\\.[^\\s]');
            if (emailRegex.test(String(self.query()))) {
                return true;
            } else {
                return false;
            }
        });

        self.foundResults = ko.pureComputed(function () {
            return self.query() && self.results().length && !self.parentImport();
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
    gotoInviteFromExplicitLink: function () {
        var self = this;
        self.inviteFromExplicitLink = true;
        self.gotoInvite();
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
        this.parentImport(false);
        this.pageToGet(0);
        this.fetchResults();
    },
    fetchResults: function () {
        if (this.parentImport()){
            this.importFromParent();
        } else {
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
                        self.addNewPaginators(false);
                    }
                );
            } else {
                self.results([]);
                self.currentPage(0);
                self.totalPages(0);
                self.doneSearching(true);
            }
        }
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
            var contributors = response.data.map(function (contributor) {
                // contrib ID has the form <nodeid>-<userid>
                return contributor.id.split('-')[1];
            });
            self.contributors(contributors);
        });
    },
    startSearchParent: function () {
        this.parentImport(true);
        this.importFromParent();
    },
    importFromParent: function () {
        var self = this;
        self.doneSearching(false);
        self.notification(false);
        return $.getJSON(
            self.nodeApiUrl + 'get_contributors_from_parent/', {},
            function (result) {
                var contributors = result.contributors.map(function (user) {
                    var added = (self.contributors().indexOf(user.id) !== -1);
                    var updatedUser = $.extend({}, user, {added: added});

                    var user_permission = self.permissionList.find(function (permission) {
                        return permission.value === user.permission;
                    });
                    updatedUser.permission = ko.observable(user_permission);

                    return updatedUser;
                });
                var pageToShow = [];
                var startingSpot = (self.pageToGet() * 5);
                if (contributors.length > startingSpot + 5){
                    for (var iterate = startingSpot; iterate < startingSpot + 5; iterate++) {
                        pageToShow.push(contributors[iterate]);
                    }
                } else {
                    for (var iterateTwo = startingSpot; iterateTwo < contributors.length; iterateTwo++) {
                        pageToShow.push(contributors[iterateTwo]);
                    }
                }
                self.doneSearching(true);
                self.selection(contributors);
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
            return _('Full Name is required.');
        }
        if (self.inviteEmail() && !$osf.isEmail(self.inviteEmail().replace(/^\s+|\s+$/g, ''))) {
            return _('Not a valid email address.');
        }
        // Make sure that entered email is not already in selection
        for (var i = 0, contrib; contrib = self.selection()[i]; ++i) {
            if (contrib.email) {
                var contribEmail = contrib.email.toLowerCase().trim();
                if (contribEmail === self.inviteEmail().toLowerCase().trim()) {
                    return sprintf(_('%1$s is already in queue.'),self.inviteEmail());
                }
            }
        }
        return true;
    },
    postInvite: function () {
        var self = this;
        self.inviteError('');
        self.canSubmit(false);

        var validated = self.validateInviteForm();
        if (typeof validated === 'string') {
            self.inviteError(validated);
            self.canSubmit(true);
            return false;
        }
        return self.postInviteRequest(self.inviteName(), self.inviteEmail().replace(/^\s+|\s+$/g, ''));
    },
    add: function (data) {
        var self = this;
        data.permission = ko.observable(self.permissionList[1]); //default permission write
        // All manually added contributors are visible
        data.visible = true;
        this.selection.push(data);
        self.query('');
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
        self.query('');
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
        self.canSubmit(false);
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
                if (self.callback) {
                    self.callback(response);
                }
            } else {
                window.location.reload();
            }
        }).fail(function (xhr, status, error) {
            var errorMessage = lodashGet(xhr, 'responseJSON.message') || (sprintf(_('There was a problem trying to add contributors%1$s.') , osfLanguage.REFRESH_OR_SUPPORT));
            $osf.growl(_('Could not add contributors'), errorMessage);
            Raven.captureMessage(_('Error adding contributors'), {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        }).always(function () {
            self.hide();
            $osf.unblock();
            self.canSubmit(true);
        });
    },
    clear: function () {
        var self = this;
        self.page('whom');
        self.parentImport(false);
        self.query('');
        self.results([]);
        self.selection([]);
        self.childrenToChange([]);
        self.notification(false);
    },
    postInviteRequest: function (fullname, email) {
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
        self.query('');
        self.results([]);
        self.page('whom');
        self.add(result.contributor);
        self.canSubmit(true);
    },
    onInviteError: function (xhr) {
        var self = this;
        var response = JSON.parse(xhr.responseText);
        // Update error message
        self.inviteError(response.message);
        self.canSubmit(true);
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
            $osf.growl('Error', _('Unable to retrieve project settings'));
            Raven.captureMessage(_('Could not GET project settings.'), {
                extra: {
                    url: treebeardUrl, status: status, error: error
                }
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
    self.viewModel.fetchNodeTree(treebeardUrl).done(function(response) {
        new NodeSelectTreebeard('addContributorsTreebeard', response, self.viewModel.nodesState);
    });
    $osf.applyBindings(self.viewModel, self.$element[0]);
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
