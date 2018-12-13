var ko = require('knockout');
var moment = require('moment');
require('pikaday');
require('pikaday-css');
var bootbox = require('bootbox');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('./osfHelpers');
var language = require('js/osfLanguage').registrations;
var Treebeard = require('treebeard');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');

var template = require('raw-loader!templates/registration-modal.html');
$(document).ready(function() {
    $('body').append(template);
});

var MAKE_PUBLIC = {
    value: 'immediate',
    message: 'Make registration public immediately'
};
var MAKE_EMBARGO = {
    value: 'embargo',
    message: 'Enter registration into embargo'
};
var MESSAGES = {
    selectTitle: 'Register Project',
    confirmTitle: 'Confirm',
    embargoTitle: 'Embargo',
    selectNodes: 'Select components to be included in the registration.',
};

function _flattenNodeTree(nodeTree) {
    var ret = [];
    var stack = [nodeTree];
    while (stack.length) {
        var node = stack.pop();
        if(node.children){
            $.each(node.children, function(_, child){
                child.parent = node.node.id;
            });
            stack = stack.concat(node.children);
        }
        ret.push(node);

    }
    return ret;
}

/**
 * take treebeard tree structure of nodes and get a dictionary of parent node and all its
 * children
 */
function getNodesOriginal(nodeTree, nodesOriginal) {
    var flatNodes = _flattenNodeTree(nodeTree);
    $.each(flatNodes, function(_, nodeMeta) {
        nodesOriginal[nodeMeta.node.id] = {
            selected: true,
            id: nodeMeta.node.id,
            title: nodeMeta.node.title,
            isAdmin: nodeMeta.node.is_admin,
            changed: false,
            parent: nodeMeta.parent
        };
    });
    nodesOriginal[nodeTree.node.id].isRoot = true;
    nodesOriginal[nodeTree.node.id].disabled = true; // The user must register the root.
    return nodesOriginal;
}


// Expand all children
function expandOnLoad() {
    var tb = this;  // jshint ignore: line
    for (var i = 0; i < tb.treeData.children.length; i++) {
        var parent = tb.treeData.children[i];
        tb.updateFolder(null, parent);
    }
}

function NodesRegisterTreebeard(divID, data, nodesState, nodesOriginal) {
    var tbOptions = $.extend({}, projectSettingsTreebeardBase.defaults, {
        divID: divID,
        filesData: data,
        naturalScrollLimit: 0,
        rowHeight: 35,
        hScroll: 0,
        columnTitles: function () {
            return [
                {
                    title: 'checkBox',
                    width: '4%',
                    sortType: 'text',
                    sort: true
                },
                {
                    title: 'project',
                    width: '96%',
                    sortType: 'text',
                    sort: true
                }
            ];
        },
        ondataload : function () {
            var tb = this;
            expandOnLoad.call(tb);
        },
        resolveRows: function nodesPrivacyResolveRows(item) {
            var tb = this;
            var columns = [];
            var id = item.data.node.id;
            var nodesStateLocal = ko.toJS(nodesState());
            item.data.node.selected = nodesStateLocal[id].selected;
            item.data.node.disabled = nodesStateLocal[id].disabled;
            columns.push(
                {
                    data: 'action',
                    sortInclude: false,
                    filter: false,
                    custom: function () {
                        return m('input[type=checkbox]', {
                            disabled: item.data.node.disabled,
                            onclick: function () {
                                item.data.node.selected = !item.data.node.selected;
                                item.open = true;
                                nodesStateLocal[id].selected = item.data.node.selected;
                                if (nodesStateLocal[id].selected !== nodesOriginal[id].local) {
                                    nodesStateLocal[id].changed = true;
                                }
                                else {
                                    nodesStateLocal[id].changed = false;
                                }
                                nodesState(nodesStateLocal);
                                tb.updateFolder(null, item);
                            },
                            checked: nodesState()[id].selected
                        });
                    }
                },
                {
                    data: 'project',  // Data field name
                    folderIcons: true,
                    filter: true,
                    sortInclude: false,
                    hideColumnTitles: false,
                    custom: function () {
                        return m('span', item.data.node.title);
                    }
                }
            );
            return columns;
        }
    });
    var grid = new Treebeard(tbOptions);
}


var RegistrationViewModel = function(confirm, prompts, validator, options) {
    var self = this;
    // Wire up the registration options.
    self.requiresApproval = options.requiresApproval;

    self.registrationOptions = [
        MAKE_PUBLIC,
        MAKE_EMBARGO
    ];
    self.registrationChoice = ko.observable(MAKE_PUBLIC.value);


    // Wire up the embargo option.

    self.requestingEmbargo = ko.computed(function() {
        var choice = self.registrationChoice();
        return choice === MAKE_EMBARGO.value;
    });
    self.requestingEmbargo.subscribe(function(requestingEmbargo) {
        self.showEmbargoDatePicker(requestingEmbargo);
    });
    self.showEmbargoDatePicker = ko.observable(false);
    self.pikaday = ko.observable(new Date());  // interacts with a datePicker from koHelpers.js


    // Wire up embargo validation.
    // ---------------------------
    // All registrations undergo an approval process before they're made public
    // (though details differ based on the type of registration). We try to
    // require (for some reason) that the embargo lasts at least as long as the
    // approval period. On the other hand, we don't want (for some reason)
    // embargos to be *too* long.

    self.embargoEndDate = ko.computed(function() {
        return moment(new Date(self.pikaday()));
    });

    self._now = function() { return moment(); };  // this is a hook for testing

    self.embargoIsLongEnough = function(end) {
        var min = self._now().add(2, 'days');
        return end.isAfter(min);
    };

    self.embargoIsShortEnough = function(end) {
        var max = self._now().add(4, 'years').subtract(1, 'days');
        return end.isBefore(max);
    };

    var validation = [{
        validator: self.embargoIsLongEnough,
        message: 'Embargo end date must be at least three days in the future.'
    }, {
        validator: self.embargoIsShortEnough,
        message: 'Embargo end date must be less than four years in the future.'
    }];
    if(validator) {
        validation.unshift(validator);
    }
    self.embargoEndDate.extend({
        validation: validation
    });


    // Wire up the modal actions.

    self.canRegister = ko.pureComputed(function() {
        if (self.requestingEmbargo()) {
            return self.embargoEndDate.isValid();
        }
        return true;
    });

    self.confirm = confirm;
    self.preRegisterPrompts = prompts;
    self.close = bootbox.hideAll;

    self.SELECT = 'select';
    self.CONFIRM = 'confirm';
    self.EMBARGO = 'embargo';

    self.treebeardUrl = window.contextVars.node.urls.api  + 'tree/';
    self.nodesOriginal = {};

    //state of current nodes
    self.nodesState = ko.observableArray();
    self.nodesState.subscribe(function(newValue) {
        for (var key in newValue) {
            if (newValue[key].selected !== self.nodesOriginal[key].selected) {
                newValue[key].changed = true;
            }
            else {
                newValue[key].changed = false;
            }
        }
        m.redraw(true);
    });

    self.nodesSelected = ko.computed(function() {
        var selected = [];
        var nodesState = ko.toJS(self.nodesState());
        for (var node in nodesState) {
            if (nodesState[node].selected) {
                selected.push(nodesState[node]);
            }
        }
        return selected;
    });

    self.invalidSelection = ko.computed(function() {
        var nodesState = ko.toJS(self.nodesState());
        for (var node in nodesState) {
            if (nodesState[node].selected){
                if (nodesState[node].parent && !nodesState[nodesState[node].parent].selected) {
                    return true;
                }
            }
        }
        return false;
    });

    self.validationWarning = ko.computed(function() {
        if(self.invalidSelection()){
            return '<span class="text-danger">To register a subcomponent, you must also register the component above it.</span>';
        }
    });

    //original node state on page load
    $('#nodesRegister').on('hidden.bs.modal', function () {
        self.clear();
    });

    // FIXME: Metaschemas that require approval (e.g. prereg)
    // go through APIv1 for submission, which doesn't support
    // partial registrations. This check avoids showing
    // the partial reg UI.
    self.page = ko.observable(self.requiresApproval ? self.EMBARGO : self.SELECT);

    self.pageTitle = ko.computed(function() {
        return {
            select: MESSAGES.selectTitle,
            confirm: MESSAGES.confirmTitle,
            embargo: MESSAGES.embargoTitle
        }[self.page()];
    });

    self.nodesMessage = ko.computed(function() {
        return {
            select: MESSAGES.selectNodes,
            confirm: MESSAGES.confirmWarning
        }[self.page()];
    });

    if (!self.requiresApproval) {
        self.fetchNodeTree().done(function(response) {
            new NodesRegisterTreebeard('nodesRegisterTreebeard', response, self.nodesState, self.nodesOriginal);
        });
    }

    self.noComponents = ko.computed(function() {
        return Object.keys(self.nodesState()).length === 1;
    });
};

RegistrationViewModel.prototype.show = function() {
    var self = this;
    bootbox.dialog({
        size: 'medium',
        message: function () {
            ko.renderTemplate('registrationChoiceModal', self, {}, this);
        }
    });
};

RegistrationViewModel.prototype.register = function() {
    var end = this.embargoEndDate();
    this.confirm({
        nodesToRegister: this.nodesSelected(),
        registrationChoice: this.registrationChoice(),
        embargoEndDate: end,
        embargoIsLongEnough: this.embargoIsLongEnough(end),
        embargoIsShortEnough: this.embargoIsShortEnough(end)
    });
};

RegistrationViewModel.prototype.selectProjects = function() {
    this.page(this.SELECT);
};

RegistrationViewModel.prototype.confirmPage =  function() {
    this.page(this.CONFIRM);
};

RegistrationViewModel.prototype.embargoPage =  function() {
    this.page(this.EMBARGO);
};

RegistrationViewModel.prototype.clear = function() {
    this.selectNone();
};

RegistrationViewModel.prototype.selectAll = function() {
    var nodesState = ko.toJS(this.nodesState());
    for (var node in nodesState) {
        nodesState[node].selected = true;
        nodesState[node].changed = nodesState[node].selected !== this.nodesOriginal[node].selected;
    }
    this.nodesState(nodesState);
    m.redraw(true);
};

RegistrationViewModel.prototype.selectNone = function() {
    var nodesState = ko.toJS(this.nodesState());
    for (var node in nodesState) {
        if (!nodesState[node].isRoot) {
            nodesState[node].selected = false;
            nodesState[node].changed = nodesState[node].selected !== this.nodesOriginal[node].selected;
        }
    }
    this.nodesState(nodesState);
    m.redraw(true);
};

RegistrationViewModel.prototype.back = function() {
    this.page(this.SELECT);
};

RegistrationViewModel.prototype.fetchNodeTree = function() {
    var self = this;
    return $.ajax({
        url: self.treebeardUrl,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        self.nodesOriginal = getNodesOriginal(response[0], self.nodesOriginal);
        var nodesState = $.extend(true, {}, self.nodesOriginal);
        self.nodesState(nodesState);
        if(Object.keys(nodesState).length === 1){ // If there are no components skip to confirmation.
            self.page(self.EMBARGO);
        } else {
            self.page(self.SELECT);
        }
    }).fail(function(xhr, status, error) {
        $osf.growl('Error', 'Unable to retrieve project settings');
        Raven.captureMessage('Could not GET project settings.', {
            extra: {
                url: self.treebeardUrl, status: status, error: error
            }
        });
    });
};

module.exports = {
    ViewModel: RegistrationViewModel
};
