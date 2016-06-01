'use strict';
var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');

var ViewModel = function(data) {
    var self = this;
    self.treebeardUrl = data.node.urls.api + 'tree/';
    self.loading = ko.observable(false);
    self.showAdd = ko.observable(false);
    self.institutionHref = ko.observable('');
    self.userInstitutions = data.currentUser.institutions;
    self.userInstitutionsIds = self.userInstitutions.map(function(item){return item.id;});
    self.affiliatedInstitutions = ko.observableArray(data.node.institutions);

    self.affiliatedInstitutionsIds = ko.computed(function() {
        return self.affiliatedInstitutions().map(function(item){return item.id;});
    });
    self.availableInstitutions = ko.observableArray(self.userInstitutions.filter(function(each){
        return ($.inArray(each.id, self.affiliatedInstitutionsIds())) === -1;
    }));

    self.availableInstitutionsIds = ko.computed(function() {
        return self.availableInstitutions().map(function(item){return item.id;});
    });

    //Has child nodes
    self.hasChildren = ko.observable(false);

    //user chooses to delete all nodes
    self.modifyChildren = ko.observable(false);
    self.nodesOriginal = ko.observable();
    self.isAddInstitution = ko.observable(false);
    self.needsWarning = ko.observable(false);

    self.buttonInfo = ko.computed(function() {
        return {
            buttonLabel: self.isAddInstitution() ? 'Add institution' : 'Remove institution',
            buttonColor: self.isAddInstitution() ? 'btn-success' : 'btn-danger'
        };
    });


    self.modifyDialog = function (item) {
        var message;
        var modifyOneMessage;
        var modifyAllMessage;
        var htmlMessage;
        if (self.isAddInstitution()) {
            message = 'Add <b>' + item.name + '</b> to <b>' + data.node.title + '</b> or to <b>' +
                data.node.title + '</b> and every component in it?<br><br>';
            modifyOneMessage = 'Add to <b>' +  data.node.title + '</b>.',
            modifyAllMessage = 'Add to <b>' +  data.node.title + '</b> and every component for which you have permission.';
        }
        else {
            message = 'Remove <b>' + item.name + '</b> from <b>' + data.node.title + '</b> or from <b>' +
                data.node.title + '</b> and every component in it?<br><br>';
            modifyOneMessage = 'Remove from <b>' +  data.node.title + '</b>.',
            modifyAllMessage = 'Remove from <b>' +  data.node.title + '</b> and every component for which you have permission.';
        }
        if (self.needsWarning()) {
            message += '<div class="text-danger f-w-xl">Warning, you are not affiliated with <b>' + item.name +
                    '</b>.  If you remove it from your project, you cannot add it back.</div></br>';
        }
        //If the Institution has children, give the choice to select.  If not, that means a warning is necessary.
        if (self.hasChildren()) {
            htmlMessage = '<div class="row">  ' +
                        '<div class="col-md-12"> ' +
                        '<span>' + message + '</span> ' +
                        '<div class="radio" > <label for="selectOne"> ' +
                        '<input type="radio" id="selectOne" type="radio" name="radioBoxGroup"' +
                        ' value="false" checked="checked"> ' + modifyOneMessage + ' </div></label> ' +
                        '<div class="radio"> <label for="selectAll"> ' +
                        '<input type="radio" id="selectAll" type="radio" name="radioBoxGroup" value="true"> ' +
                        modifyAllMessage + ' </label> ' + '</div>' + '</div>';
        }
        else {
            message = 'Remove <b>' + item.name + '</b> from <b>' + data.node.title + '</b>.<br><br>' +
                '<div class="text-danger f-w-xl">Warning, you are not affiliated with <b>' + item.name +
                '</b>.  If you remove it from your project, you cannot add it back.</div></br>';
            htmlMessage = '<div class="row">  ' +
                        '<div class="col-md-12"> ' +
                        '<span>' + message + '</span> ' +
                        '</div>' + '</div>';
        }
        bootbox.dialog({
                title: self.pageTitle(),
                onEscape: function () {
                },
                backdrop: true,
                closeButton: true,
                message: htmlMessage,
                buttons: {
                    cancel: {
                        label: 'Cancel',
                        className: 'btn-default',
                        callback: function () {
                        }
                    },
                    success: {
                        label: self.buttonInfo().buttonLabel,
                        className: self.buttonInfo().buttonColor,
                        callback: function () {
                            self._modifyInst(item);
                        }
                    }
                }
            }
        ).on('shown.bs.modal', function(e) {
            if($('input:radio[name=radioBoxGroup]').length) {
                $('input:radio[name=radioBoxGroup]').click(function() {
                    self.modifyChildren($(this).val());

                });
            }
        });
    };

    self.pageTitle = ko.computed(function () {
        return self.isAddInstitution() ? 'Add institution' : 'Remove institution';
    });

    self.institutionInNoChildren = function(institutionID) {
        for (var key in self.nodesOriginal()) {
            if (self.nodesOriginal()[self.nodeParent].id !== key) {
                if (self.nodesOriginal()[key].institutions.indexOf(institutionID) > -1 &&
                    self.nodesOriginal()[key].isAdmin) {
                    return false;
                }
            }
        }
        return true;
    };

    self.institutionInAllChildren = function(institutionID) {
        for (var key in self.nodesOriginal()) {
            if (self.nodesOriginal()[self.nodeParent].id !== key) {
                if (self.nodesOriginal()[key].institutions.indexOf(institutionID) === -1 &&
                    self.nodesOriginal()[key].isAdmin) {
                    return false;
                }
            }
        }
        return true;
    };

    self.submitInst = function (item) {
        self.isAddInstitution(true);
        self.needsWarning(false);
        if ((self.hasChildren() && !self.institutionInAllChildren(item.id))) {
            self.modifyDialog(item);
        }
        else {
            return self._modifyInst(item);
        }

    };

    self.clearInst = function(item) {
        self.needsWarning((self.userInstitutionsIds.indexOf(item.id) === -1));
        self.isAddInstitution(false);
        if ((self.hasChildren() && !self.institutionInNoChildren(item.id)) || self.needsWarning()) {
            self.modifyDialog(item);
        }
        else {
            return self._modifyInst(item);
        }
    };

    self._modifyInst = function(item) {
        var index;
        var url = data.apiV2Prefix + 'institutions/' + item.id + '/relationships/nodes/';
        var ajaxJSONType = self.isAddInstitution() ? 'POST': 'DELETE';
        var nodesToModify = [];
        self.loading(true);
        if (self.modifyChildren()) {
            for (var node in self.nodesOriginal()) {
                if (self.nodesOriginal()[node].isAdmin) {
                    nodesToModify.push({'type': 'nodes', 'id': self.nodesOriginal()[node].id});
                }
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
            if (self.isAddInstitution()) {
                index = self.availableInstitutionsIds().indexOf(item.id);
                var added = self.availableInstitutions.splice(index, 1)[0];
                self.affiliatedInstitutions.push(added);
            }
            else {
                index = self.affiliatedInstitutionsIds().indexOf(item.id);
                var removed = self.affiliatedInstitutions.splice(index, 1)[0];
                if (self.userInstitutionsIds.indexOf(removed.id) > -1) {
                    self.availableInstitutions.push(removed);
                }
            }
            self.loading(false);
            self.modifyChildren(false);
            //fetchNodeTree is called to refresh self.nodesOriginal after a state change.  This is the simplest way to
            //update state check if the modal is necessary.
            self.fetchNodeTree(self.treebeardUrl);
        }).fail(function (xhr, status, error) {
            $osf.growl('Unable to modify the institution on this node. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
            Raven.captureMessage('Unable to modify this institution!', {
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
            self.hasChildren(Object.keys(nodesOriginal).length > 1);
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
    self.viewModel.fetchNodeTree(self.viewModel.treebeardUrl);
    $osf.applyBindings(this.viewModel, selector);

};

module.exports = {
    InstitutionProjectSettings: InstitutionProjectSettings,
    ViewModel: ViewModel
};
