'use strict';
var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

var ViewModel = function(data) {
    var self = this;
    self.url = $osf.apiV2Url('/nodes/', {'query': 'filter[root]=' + data.node.rootId + '&format=json&version=2.1'});
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

    self.childNodes = ko.observable({});
    self.nodeId = ko.observable(data.node.id);
    self.rootId = ko.observable(data.node.rootId);
    self.childExists = ko.observable(data.node.childExists);
    self.isRegistration = ko.observable(data.node.isRegistration);

    //user chooses to delete all nodes
    self.modifyChildren = ko.observable(false);
    self.isAddInstitution = ko.observable(false);
    self.needsWarning = ko.observable(false);

    self.buttonInfo = ko.computed(function() {
        return {
            buttonLabel: self.isAddInstitution() ? _('Add institution') : _('Remove institution'),
            buttonColor: self.isAddInstitution() ? 'btn-success' : 'btn-danger'
        };
    });


    self.modifyDialog = function (item) {
        var message;
        var modifyOneMessage;
        var modifyAllMessage;
        var htmlMessage;
        if (self.isAddInstitution()) {
            message = sprintf(_('Add <b>%1$s</b> to <b>%2$s</b> or to <b>%3$s</b> and every component in it?<br><br>'),item.name,data.node.title,data.node.title);
            modifyOneMessage = sprintf(_('Add to <b>%1$s</b>.'),data.node.title),
            modifyAllMessage = sprintf(_('Add to <b>%1$s</b> and every component for which you have permission.'),data.node.title);
        }
        else {
            message = sprintf(_('Remove <b>%1$s</b> from <b>%2$s</b> or from <b>%3$s</b> and every component in it?<br><br>'),item.name,data.node.title,data.node.title);
            modifyOneMessage = sprintf(_('Remove from <b>%1$s</b>.'),data.node.title),
            modifyAllMessage = sprintf(_('Remove from <b>%1$s</b> and every component for which you have permission.'),data.node.title);
        }
        if (self.needsWarning()) {
            message += '<div class="text-danger f-w-xl">' + sprintf(_('Warning, you are not affiliated with <b>%1$s</b>.') , item.name) +
                    _(' If you remove it from your project, you cannot add it back.</div></br>');
        }
        //If the Institution has children, give the choice to select.  If not, that means a warning is necessary.
        if (self.childExists()) {
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
            message = sprintf(_('Remove <b>%1$s</b> from <b>%2$s</b>.') ,item.name, data.node.title) + '<br><br>' +
                '<div class="text-danger f-w-xl">' + sprintf(_('Warning, you are not affiliated with <b>%1$s</b>.') , item.name) +
                _(' If you remove it from your project, you cannot add it back.</div></br>');
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
                        label: _('Cancel'),
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
        return self.isAddInstitution() ? _('Add institution') : _('Remove institution');
    });

    self.submitInst = function (item) {
        self.isAddInstitution(true);
        self.needsWarning(false);
        if (self.childExists()) {
            self.modifyDialog(item);
        }
        else {
            return self._modifyInst(item);
        }

    };

    self.clearInst = function(item) {
        self.needsWarning((self.userInstitutionsIds.indexOf(item.id) === -1));
        self.isAddInstitution(false);
        if (self.childExists() || self.needsWarning()) {
            self.modifyDialog(item);
        }
        else {
            return self._modifyInst(item);
        }
    };

    self._modifyInst = function(item) {
        self.loadingBootbox = bootbox.dialog({
            backdrop: true,
            closeButton: false,
            message: '<div class="spinner-loading-wrapper"><div class="ball-scale ball-scale-blue"><div></div></div><p class="m-t-sm fg-load-message"> ' + _('Updating affiliation... this may take a minute.') + '</p></div>',
        });
        var url = '';
        var nodesToModify = [];
        if (self.isRegistration()) {
            url = data.apiV2Prefix + 'institutions/' + item.id + '/relationships/registrations/';
            nodesToModify = [{'type': 'registrations', 'id': self.nodeId()}];
        } else {
            url = data.apiV2Prefix + 'institutions/' + item.id + '/relationships/nodes/';
            nodesToModify = [{'type': 'nodes', 'id': self.nodeId()}];
            if (self.modifyChildren()) {
                for (var node in self.childNodes()) {
                    if (self.childNodes()[node].hasPermissions) {
                        nodesToModify.push({'type': 'nodes', 'id': node});
                    }
                }
            }
        }
        self.loading(true);
        var ajaxJSONType = self.isAddInstitution() ? 'POST': 'DELETE';
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
            var index;
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
        }).fail(function (xhr, status, error) {
            $osf.growl(sprintf(_('Unable to modify the institution on this node. Please try again. If the problem persists, email %1$s') , $osf.osfSupportLink()));
            Raven.captureMessage(_('Unable to modify this institution!'), {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        }).always(function() {
            self.loadingBootbox.modal('hide');
            self.modifyChildren(false);
            self.loading(false);
            //fetchNodes is called to refresh self.nodesOriginal after a state change.  This is the simplest way to
            //update state to check if the modal is necessary.
            self.fetchNodes(self.url);
        });
    };
};

/**
 * takes raw nodes from fetch and formats data for self.nodes
 */
ViewModel.prototype.formatNodes = function(rawNodes) {
    var self = this;
    var nodes = {};

    // if parent is root it will still be included, prune it
    delete rawNodes[self.nodeId()];
    $.each(rawNodes, function(n) {
        var id = rawNodes[n].id;
        var branch = {};
        branch.hasPermissions = rawNodes[n].attributes.current_user_permissions.indexOf('write') > -1;
        nodes[id] = branch;
    });
    self.childNodes(nodes);
};

/**
 * get nodes off root from API V2
 */
ViewModel.prototype.fetchNodes = function(url) {
    var self = this;
    if(!self.childExists()){
        return;
    }
    var responseArray = new $osf.getAllPagesAjaxJSON('GET', url, {isCors: true});
    responseArray.done(function(data) {
        var rd = $osf.mergePagesAjaxJSON(data);
        var rawNodes = self.nodeId() === self.rootId() ? rd : $osf.getAllNodeChildrenFromNodeList(self.nodeId(), rd);
        self.formatNodes(rawNodes);

    }).fail(function (xhr, status, error) {
        $osf.growl('Error', _('Unable to retrieve project settings'));
        Raven.captureMessage(_('Could not GET project settings.'), {
            extra: {
                url: url, status: status, error: error
            }
        });
    });
};

var InstitutionProjectSettings = function(selector, data)  {
    this.viewModel = new ViewModel(data);
    var self = this;
    self.viewModel.fetchNodes(self.viewModel.url);
    $osf.applyBindings(this.viewModel, selector);

};

module.exports = {
    InstitutionProjectSettings: InstitutionProjectSettings,
    ViewModel: ViewModel
};
