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

    self.hasChildren = ko.observable(false);
    self.title = 'Add Institution';
    self.nodesOriginal = {};
    self.isAddInstitution = ko.observable(false);
    //state of current nodes
    //nodesState is passed to nodesSelectTreebeard which can update it and key off needed action.
    // self.nodesState.subscribe(function (newValue) {
    //     //The subscribe causes treebeard changes to change which nodes will be affected
    //     var childrenToChange = [];
    //     for (var key in newValue) {
    //         newValue[key].changed = newValue[key].checked !== self.nodesOriginal[key].checked;
    //         if (newValue[key].changed && key !== self.nodeId) {
    //             childrenToChange.push(key);
    //         }
    //     }
    //     self.childrenToChange(childrenToChange);
    //     m.redraw(true);
    // });

    self.setDialog = ko.computed( function() {
        return true;
    });


    // self.instModalButtons = ko.computed(function() {
    //     var buttons = {
    //         confirm: {
    //             label: 'Add email',
    //             className: 'btn-success',
    //             callback: function () {
    //                 $osf.putJSON(
    //                     confirmedEmailURL,
    //                     email
    //                 ).done(function () {
    //                     $osf.growl('Success', confirmMessage, 'success', 3000);
    //                     confirmEmails(emailsToAdd.slice(1));
    //                 }).fail(function (xhr, textStatus, error) {
    //                     Raven.captureMessage('Could not add email', {
    //                         url: confirmedEmailURL,
    //                         textStatus: textStatus,
    //                         error: error
    //                     });
    //                     $osf.growl('Error',
    //                         confirmFailMessage,
    //                         'danger'
    //                     );
    //                 });
    //             }
    //         }
    //     };

            // cancel: {
            //     label: 'Do not add email',
            //     className: 'btn-default',
            //     callback: function () {
            //         $.ajax({
            //             type: 'delete',
            //             url: confirmedEmailURL,
            //             contentType: 'application/json',
            //             dataType: 'json',
            //             data: JSON.stringify(email)
            //         }).done(function () {
            //             $osf.growl('Warning', nopeMessage, 'warning', 8000);
            //             confirmEmails(emailsToAdd.slice(1));
            //         }).fail(function (xhr, textStatus, error) {
            //             Raven.captureMessage('Could not remove email', {
            //                 url: confirmedEmailURL,
            //                 textStatus: textStatus,
            //                 error: error
            //             });
            //             $osf.growl('Error',
            //                 cancelFailMessage,
            //                 'danger'
            //             );
            //         });
            //     }
            // }
    //     if (self.haschildren()) {
    //
    //     }
    // });


    var manageInstModal = function () {
        // bootbox.dialog({
        //     title: self.title,
        //     message: requestMessage,
        //     onEscape: function () {
        //
        //     },
        //     backdrop: true,
        //     closeButton: true,
        //     buttons: self.buttons()
        // });
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

        }
        else {
            return self._modifyInst(item);
        }

        var url = data.apiV2Prefix + 'nodes/' + data.node.id + '/relationships/institutions/';
        var inst = self.selectedInstitution();

        // return $osf.ajaxJSON(
        //     'POST',
        //     url,
        //     {
        //         'isCors': true,
        //         'data': {
        //              'data': [{'type': 'institutions', 'id': item.id}]
        //         },
        //         fields: {xhrFields: {withCredentials: true}}
        //     }
        // ).done(function (response) {
        //     var indexes = self.availableInstitutions().map(function(each){return each.id;});
        //     var index = indexes.indexOf(self.selectedInstitution());
        //     var added = self.availableInstitutions().splice(index, 1)[0];
        //     self.availableInstitutions(self.availableInstitutions());
        //     self.affiliatedInstitutions().push(added);
        //     self.affiliatedInstitutions(self.affiliatedInstitutions());
        //     self.showAdd(false);
        // }).fail(function (xhr, status, error) {
        //     $osf.growl('Unable to add institution to this node. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
        //     Raven.captureMessage('Unable to add institution to this node', {
        //         extra: {
        //             url: url,
        //             status: status,
        //             error: error
        //         }
        //     });
        // });
    };
    self.clearInst = function(item) {
        self.isAddInstitution(false);
        bootbox.confirm({
            title: 'Are you sure you want to remove institutional affiliation from your project?',
            message: 'You are about to remove affiliation with ' + item.name + ' from this project. ' + item.name + ' branding will not longer appear on this project, and the project will not be discoverable on the ' + item.name + ' landing page.',
            callback: function (confirmed) {
                if (confirmed) {
                    self._modifyInst(item);
                }
            },
            buttons:{
                confirm:{
                    label:'Remove affiliation'
                }
            }
        });
    };

    self._submitInst = function(item) {
        var url = data.apiV2Prefix + 'nodes/' + data.node.id + '/relationships/institutions/';

        return $osf.ajaxJSON(
            'POST',
            url,
            {
                'isCors': true,
                'data': {
                     'data': [{'type': 'institutions', 'id': item.id}]
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

    self._clearInst = function(item) {
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

    self._modifyInst = function(item) {
        var url = data.apiV2Prefix + 'nodes/' + data.node.id + '/relationships/institutions/';
        var ajaxJSONType = self.isAddInstitution() ? 'POST': 'DELETE';
        return $osf.ajaxJSON(
            ajaxJSONType,
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
            self.hasChildren(self.nodesOriginal.length > 1);
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
