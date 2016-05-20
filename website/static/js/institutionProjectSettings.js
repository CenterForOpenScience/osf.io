'use strict';
var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var m = require('mithril');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');

var ViewModel = function(data) {
    var self = this;
    self.loading = ko.observable(true);
    self.showAdd = ko.observable(false);
    self.institutionHref = ko.observable('');
    self.userInstitutions = window.contextVars.currentUser.institutions;
    var userInstitutionsIds = self.userInstitutions.map(function (item) {
        return item.id;
    });
    self.userInstitutionsIds = ko.observable(userInstitutionsIds);
    self.selectedInstitution = ko.observable();
    self.affiliatedInstitutions = ko.observable(window.contextVars.node.institutions);
    self.affiliatedInstitutionsIds = self.affiliatedInstitutions().map(function (item) {
        return item.id;
    });

    //Has child nodes
    self.hasChildren = ko.observable(false);

    //user chooses to delete all nodes
    self.modifyChildren = ko.observable(false);
    self.title = 'Add Institution';
    self.nodesOriginal = ko.observable();
    self.isAddInstitution = ko.observable(false);
    self.needsWarning = ko.observable(false);


    self.modifyChildrenDialog = function (item) {
        var message;
        if (self.isAddInstitution()) {
            message = 'Add ' + item.name + ' to ' + window.contextVars.node.title + ' or to ' +
                item.name + ' and all its components?<br><br>';
        }
        else
            message = 'Remove ' + item.name + ' from ' + window.contextVars.node.title + ' or to ' +
                item.name + ' and all its components?<br><br>';

        if (self.needsWarning()) {
            message += '<div class="text-danger f-w-xl">Warning, you are not affialiated with <b>' + item.name +
                    '</b>.  If you remove it from your project, you cannot add it back.<div>';
        }
        bootbox.dialog({
            title: self.isAddInstitution() ? 'Add ' + item.name: 'Remove ' + item.name,
            message: message,
            onEscape: function () {
            },
            backdrop: true,
            closeButton: true,
            buttons: {
                cancel: {
                    label: 'Cancel',
                    className: 'btn-default',
                    callback: function () {
                    }
                },
                modifyOne: {
                    label: self.isAddInstitution() ? 'Add one' : 'Remove one',
                    className: 'btn-primary',
                    callback: function () {
                        self.modifyChildren(false);
                        self._modifyInst(item);
                    }
                },
                modifyAll: {
                    label: self.isAddInstitution() ? 'Add all' : 'Remove all',
                    className: 'btn-success',
                    callback: function () {
                        self.modifyChildren(true);
                        self._modifyInst(item);
                    }
                }
            }
        });
    };

    self.pageTitle = ko.computed(function () {
        return self.isAddInstitution() ? 'Add institution' : 'Remove institution';
    });

    var affiliatedInstitutionsIds = self.affiliatedInstitutions().map(function (item) {
        return item.id;
    });
    self.availableInstitutions = ko.observable(self.userInstitutions.filter(function (each) {
        return ($.inArray(each.id, affiliatedInstitutionsIds)) === -1;
    }));

    self.hasThingsToAdd = ko.computed(function () {
        return self.availableInstitutions().length ? true : false;
    });

    self.toggle = function () {
        self.showAdd(self.showAdd() ? false : true);
    };

    self.submitInst = function (item) {
        self.isAddInstitution(true);
        self.needsWarning(false);
        if (self.hasChildren()) {
            self.modifyChildrenDialog(item);
        }
        else {
            return self._modifyInst(item);
        }

    };
    self.clearInst = function(item) {
        self.needsWarning((self.userInstitutionsIds().indexOf(item.id) === -1));
        self.isAddInstitution(false);
        if (self.hasChildren()) {
            self.modifyChildrenDialog(item);
        }
        else {
            return self._modifyInst(item);
        }
    };

    self._modifyInst = function(item) {
        var url = data.apiV2Prefix + 'institutions/' + item.id + '/relationships/nodes/';
        var ajaxJSONType = self.isAddInstitution() ? 'POST': 'DELETE';
        var nodesToModify = [];
        if (self.modifyChildren()) {
            for (var node in self.nodesOriginal()) {
                nodesToModify.push({'type': 'nodes', 'id': self.nodesOriginal()[node].id});
            }
        }
        else {
                nodesToModify.push({'type': 'nodes', 'id': self.nodeParent});
        }
        return $osf.ajaxJSON(
            ajaxJSONType,
            url,
            {
                isCors: true,
                data: {
                     'data': nodesToModify
                },
                fields: {xhrFields: {withCredentials: true}}
            }
        ).done(function () {
            var indexes = self.affiliatedInstitutions().map(function(each){return each.id;});
            if (self.isAddInstitution()) {
                var index = indexes.indexOf(self.selectedInstitution());
                var added = self.availableInstitutions().splice(index, 1)[0];
                self.availableInstitutions(self.availableInstitutions());
                self.affiliatedInstitutions().push(added);
                self.affiliatedInstitutions(self.affiliatedInstitutions());
                self.showAdd(false);
            }
            else {
                var removed = self.affiliatedInstitutions().splice(indexes.indexOf(item.id), 1)[0];
                if ($.inArray(removed.id, self.userInstitutionsIds()) >= 0){
                    self.availableInstitutions().push(removed);
                }
                self.affiliatedInstitutions(self.affiliatedInstitutions());
            }
            self.availableInstitutions(self.availableInstitutions());

        }).fail(function (xhr, status, error) {
            $osf.growl('Unable to modify the institution on this node. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
            Raven.captureMessage('Unable to modufy this institution!', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    };
};

/**
 * get node tree for treebeard from API V1
 */
ViewModel.prototype.fetchNodeTree = function(treebeardUrl) {
        var nodesOriginal = {};
        var self = this;
        return $.ajax({
            url: treebeardUrl,
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
            nodesOriginal = projectSettingsTreebeardBase.getNodesOriginal(response[0], nodesOriginal);
            self.nodeParent = response[0].node.id;
            self.hasChildren(Object.keys(self.nodesOriginal).length > 1);
            self.nodesOriginal(nodesOriginal);
        }).fail(function (xhr, status, error) {
            $osf.growl('Error', 'Unable to retrieve project settings');
            Raven.captureMessage('Could not GET project settings.', {
                url: treebeardUrl, status: status, error: error
            });
        });
};

var InstitutionProjectSettings = function(selector, data)  {
    this.viewModel = new ViewModel(data);
    var self = this;
    var treebeardUrl = window.contextVars.node.urls.api + 'tree/';
    self.viewModel.fetchNodeTree(treebeardUrl);
    $osf.applyBindings(this.viewModel, selector);

};

module.exports = {
    InstitutionProjectSettings: InstitutionProjectSettings,
    ViewModel: ViewModel
};

