'use strict';
var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var m = require('mithril');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');
var NodeSelectTreebeard = require('js/nodeSelectTreebeard');

var ViewModel = function(data) {
    var self = this;
    self.loading = ko.observable(true);
    self.showAdd = ko.observable(false);
    self.institutionHref = ko.observable('');
    self.userInstitutions = window.contextVars.currentUser.institutions;
    self.userInstitutionsIds = self.userInstitutions.map(function (item) {
        return item.id;
    });
    self.selectedInstitution = ko.observable();
    self.affiliatedInstitutions = ko.observable(window.contextVars.node.institutions);

    //Has child nodes
    self.hasChildren = ko.observable(false);

    //user chooses to delete all nodes
    self.modifyChildren = ko.observable(false);
    self.title = 'Add Institution';
    self.nodesOriginal = {};
    self.isAddInstitution = ko.observable(false);


    self.modifyChildrenDialog = function(item) {

        var message = self.isAddInstitution() ?
                'Add '+ item.name + ' to ' + window.contextVars.node.title + ' or to ' +
                item.name + ' and all its components?<br><br>' :
                'Remove '+ item.name  + ' from ' + window.contextVars.node.title + ' or to ' +
                item.name + ' and all its components?<br><br>' ;

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
        if (self.hasChildren()) {
            self.modifyChildrenDialog(item);
        }
        else {
            return self._modifyInst(item);
        }

    };
    self.clearInst = function(item) {
        self.isAddInstitution(false);
        bootbox.confirm({
                title: 'Are you sure you want to remove institutional affiliation from your project?',
                message: 'You are about to remove affiliation with ' + item.name + ' from this project. ' + item.name + ' branding will not longer appear on this project, and the project will not be discoverable on the ' + item.name + ' landing page.',
                callback: function (confirmed) {
                    if (confirmed) {
                        if (self.hasChildren()) {
                            self.modifyChildrenDialog(item);
                        }
                        else {
                            self._modifyInst(item);
                        }
                    }
                },
                buttons:{
                    confirm:{
                        label:'Remove affiliation'
                    }
                }
            });
    };

    self._modifyInst = function(item) {
        var url = data.apiV2Prefix + 'institutions/' + item.id + '/relationships/nodes/';
        var ajaxJSONType = self.isAddInstitution() ? 'POST': 'DELETE';
        var nodesToModify = [];
        if (self.modifyChildren()) {
            for (var node in self.nodesOriginal) {
                nodesToModify.push({'type': 'nodes', 'id': self.nodesOriginal[node].id});
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
                if ($.inArray(removed.id, self.userInstitutionsIds) >= 0){
                    self.availableInstitutions().push(removed);
                }
                self.affiliatedInstitutions(self.affiliatedInstitutions());
            }
            self.availableInstitutions(self.availableInstitutions());

        }).fail(function (xhr, status, error) {
            $osf.growl('Unable to remove institution from this node. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
            Raven.captureMessage('Unable to remove institution from this node!', {
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
        var self = this;
        return $.ajax({
            url: treebeardUrl,
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
            self.nodesOriginal = projectSettingsTreebeardBase.getNodesOriginal(response[0], self.nodesOriginal);
            self.nodeParent = response[0].node.id;
            self.hasChildren(Object.keys(self.nodesOriginal).length > 1);
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

module.exports = InstitutionProjectSettings;
