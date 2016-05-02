'use strict';
var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');
var NodeSelectTreebeard = require('js/nodeSelectTreebeard');

var ViewModel = function(data) {
    var self = this;
    self.primaryInstitution = ko.observable('Loading...');
    self.loading = ko.observable(true);
    self.error = ko.observable(false);
    self.showAdd = ko.observable(false);
    self.institutionHref = ko.observable('');
    self.userInstitutions = window.contextVars.currentUser.institutions;
    self.userInstitutionsIds = self.userInstitutions.map(function(item){return item.id;});
    self.selectedInstitution = ko.observable();
    self.affiliatedInstitutions = ko.observable(window.contextVars.node.institutions);

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

    var affiliatedInstitutionsIds = self.affiliatedInstitutions().map(function(item){return item.id;});
    self.availableInstitutions = ko.observable(self.userInstitutions.filter(function(each){
        return ($.inArray(each.id, affiliatedInstitutionsIds)) === -1;
    }));

    self.hasThingsToAdd = ko.computed(function(){
        return self.availableInstitutions().length ? true : false;
    });

    self.toggle = function() {
        self.showAdd(self.showAdd() ? false : true);
    };

    self.submitInst = function() {
        var url = data.apiV2Prefix + 'nodes/' + data.node.id + '/relationships/institutions/';
        var inst = self.selectedInstitution();

        return $osf.ajaxJSON(
            'POST',
            url,
            {
                'isCors': true,
                'data': {
                     'data': [{'type': 'institutions', 'id': inst}]
                },
                fields: {xhrFields: {withCredentials: true}}
            }
        ).done(function (response) {
            var indexes = self.availableInstitutions().map(function(each){return each.id;});
            var index = indexes.indexOf(self.selectedInstitution());
            var added = self.availableInstitutions().splice(index, 1)[0];
            self.availableInstitutions(self.availableInstitutions());
            self.affiliatedInstitutions().push(added);
            self.affiliatedInstitutions(self.affiliatedInstitutions());
            self.showAdd(false);
        }).fail(function (xhr, status, error) {
            $osf.growl('Unable to add institution to this node. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
            Raven.captureMessage('Unable to add institution to this node', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    };
    self.clearInst = function(item) {
        var url = data.apiV2Prefix + 'nodes/' + data.node.id + '/relationships/institutions/';
        return $osf.ajaxJSON(
            'DELETE',
            url,
            {
                isCors: true,
                data: {
                     'data': [{'type': 'institutions', 'id': item.id}]
                },
                fields: {xhrFields: {withCredentials: true}}
            }
        ).done(function (response) {
            var indexes = self.affiliatedInstitutions().map(function(each){return each.id;});
            var removed = self.affiliatedInstitutions().splice(indexes.indexOf(item.id), 1)[0];
            if ($.inArray(removed.id, self.userInstitutionsIds) >= 0){
                self.availableInstitutions().push(removed);
                self.availableInstitutions(self.availableInstitutions());
            }
            self.affiliatedInstitutions(self.affiliatedInstitutions());
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
            var nodesState = $.extend(true, {}, self.nodesOriginal);
            var nodeParent = response[0].node.id;
            //parent node is changed by default
            nodesState[nodeParent].checked = true;
            //parent node cannot be changed
            nodesState[nodeParent].canWrite = false;
            self.nodesState(nodesState);
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
    self.viewModel.getContributors();
    self.viewModel.fetchNodeTree(treebeardUrl).done(function(response) {
        new NodeSelectTreebeard('addContributorsTreebeard', response, self.viewModel.nodesState);
    });$osf.applyBindings(this.viewModel, selector);

};

module.exports = InstitutionProjectSettings;
