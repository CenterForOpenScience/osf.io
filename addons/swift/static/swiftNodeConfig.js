'use strict';

var $ = require('jquery');
var ko = require('knockout');
var m = require('mithril');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var oop = require('js/oop');

var swiftSettings = require('json!./settings.json');

var OauthAddonFolderPicker = require('js/oauthAddonNodeConfig')._OauthAddonNodeConfigViewModel;

var swiftFolderPickerViewModel = oop.extend(OauthAddonFolderPicker, {

    constructor: function(addonName, url, selector, folderPicker, opts, tbOpts) {
        var self = this;
        // TODO: [OSF-7069]
        self.super.super.constructor.call(self, addonName, url, selector, folderPicker, tbOpts);
        self.super.construct.call(self, addonName, url, selector, folderPicker, opts, tbOpts);
        // Non-OAuth fields
        self.authVersion = ko.observable('v2');
        self.authUrl = ko.observable('');
        self.accessKey = ko.observable('');
        self.secretKey = ko.observable('');
        self.tenantName = ko.observable('');
        self.userDomainName = ko.observable('');
        self.projectDomainName = ko.observable('');
        // Treebeard config
        self.treebeardOptions = $.extend(
            {},
            self.treebeardOptions,
            {   // TreeBeard Options
                columnTitles: function() {
                    return [{
                        title: 'Containers',
                        width: '75%',
                        sort: false
                    }, {
                        title: 'Select',
                        width: '25%',
                        sort: false
                    }];
                },
                resolveToggle: function(item) {
                    return '';
                },
                resolveIcon: function(item) {
                    return m('i.fa.fa-folder-o', ' ');
                },
            },
            tbOpts
        );
    },

    connectAccount: function() {
        var self = this;
        var authVersion = null;
        if (self.authVersion() == 'v2') {
            authVersion = '2';
        }else if (self.authVersion() == 'v3') {
            authVersion = '3';
        }else{
            self.changeMessage('Please enter valid Identity version.', 'text-danger');
            return;
        }
        // Selection should not be empty
        if(!self.authUrl() && !self.accessKey() && !self.secretKey() && !self.tenantName()){
            self.changeMessage('Please enter all an API authentication URL, tenant name, username and password.', 'text-danger');
            return;
        }

        if (!self.authUrl() ){
            self.changeMessage('Please enter your authentication URL.', 'text-danger');
            return;
        }

        if (!self.accessKey() ){
            self.changeMessage('Please enter an API username.', 'text-danger');
            return;
        }
        if(authVersion == '3' && !self.userDomainName()) {
            self.changeMessage('Please enter a domain name for your username.', 'text-danger');
            return;
        }

        if (!self.secretKey() ){
            self.changeMessage('Please enter an API password.', 'text-danger');
            return;
        }

        if (!self.tenantName() ){
            self.changeMessage('Please enter your tenant name.', 'text-danger');
            return;
        }
        if(authVersion == '3' && !self.projectDomainName()) {
            self.changeMessage('Please enter a domain name for your project.', 'text-danger');
            return;
        }
        return $osf.postJSON(
            self.urls().create, {
                auth_version: authVersion,
                auth_url: self.authUrl(),
                access_key: self.accessKey(),
                secret_key: self.secretKey(),
                tenant_name: self.tenantName(),
                user_domain_name: self.userDomainName(),
                project_domain_name: self.projectDomainName()
            }
        ).done(function(response) {
            $osf.unblock();
            self.clearModal();
            $('#swiftInputCredentials').modal('hide');
            self.changeMessage('Successfully added Swift credentials.', 'text-success', null, true);
            self.updateFromData(response);
            self.importAuth();
        }).fail(function(xhr, status, error) {
            $osf.unblock();
            var message = '';
            var response = JSON.parse(xhr.responseText);
            if (response && response.message) {
                message = response.message;
            }
            self.changeMessage(message, 'text-danger');
            Raven.captureMessage('Could not add Swift credentials', {
                extra: {
                    url: self.urls().importAuth,
                    textStatus: status,
                    error: error
                }
            });
        });
    },
    /**
     * Tests if the given string is a valid Swift container name.
     *
     * https://docs.openstack.org/developer/swift/api/object_api_v1_overview.html
     * https://lists.launchpad.net/openstack/msg06956.html
     *
     * > Length of container names / Maximum value 256 bytes / Cannot contain the / character.
     *
     * @param {String} containerName user-provided name of container to validate
     */
    isValidContainerName: function(containerName) {
        var containerNamePattern = /^[^/]+$/;
        return containerName.length <= 256 &&
               containerNamePattern.test(containerName);
    },

    /** Reset all fields from S3 credentials input modal */
    clearModal: function() {
        var self = this;
        self.message('');
        self.messageClass('text-info');
        self.authVersion('v2');
        self.authUrl(null);
        self.secretKey(null);
        self.accessKey(null);
        self.tenantName(null);
        self.userDomainName(null);
        self.projectDomainName(null);
    },

    createContainer: function(self, containerName) {
        $osf.block();
        return $osf.postJSON(
            self.urls().createContainer, {
                container_name: containerName
            }
        ).done(function(response) {
            $osf.unblock();
            self.loadedFolders(false);
            self.activatePicker();
            var msg = 'Successfully created container "' + $osf.htmlEscape(containerName) + '". You can now select it from the list.';
            var msgType = 'text-success';
            self.changeMessage(msg, msgType, null, true);
        }).fail(function(xhr) {
            var resp = JSON.parse(xhr.responseText);
            var message = resp.message;
            var title = resp.title || 'Problem creating container';
            $osf.unblock();
            if (!message) {
                message = 'Looks like that name is taken. Try another name?';
            }
            bootbox.confirm({
                title: $osf.htmlEscape(title),
                message: $osf.htmlEscape(message),
                callback: function(result) {
                    if (result) {
                        self.openCreateContainer();
                    }
                },
                buttons:{
                    confirm:{
                        label:'Try again'
                    }
                }
            });
        });
    },

    openCreateContainer: function() {
        var self = this;

        bootbox.dialog({
            title: 'Create a new container',
            message:
                    '<div class="row"> ' +
                        '<div class="col-md-12"> ' +
                            '<form class="form-horizontal" onsubmit="return false"> ' +
                                '<div class="form-group"> ' +
                                    '<label class="col-md-4 control-label" for="containerName">Container Name</label> ' +
                                    '<div class="col-md-8"> ' +
                                        '<input id="containerName" name="containerName" type="text" placeholder="Enter container name" class="form-control" autofocus> ' +
                                        '<div>' +
                                            '<span id="containerModalErrorMessage" ></span>' +
                                        '</div>'+
                                    '</div>' +
                                '</div>' +
                            '</form>' +
                        '</div>' +
                    '</div>',
            buttons: {
                cancel: {
                    label: 'Cancel',
                    className: 'btn-default'
                },
                confirm: {
                    label: 'Create',
                    className: 'btn-success',
                    callback: function () {
                        var containerName = $('#containerName').val();

                        if (!containerName) {
                            var errorMessage = $('#containerModalErrorMessage');
                            errorMessage.text('Container name cannot be empty');
                            errorMessage[0].classList.add('text-danger');
                            return false;
                        } else if (!self.isValidContainerName(containerName)) {
                            bootbox.confirm({
                                title: 'Invalid container name',
                                message: 'Swift containers cannot contain slashes. Please try another name.',
                                callback: function (result) {
                                    if (result) {
                                        self.openCreateContainer();
                                    }
                                },
                                buttons: {
                                    confirm: {
                                        label: 'Try again'
                                    }
                                }
                            });
                        } else {
                            self.createContainer(self, containerName);
                        }
                    }
                }
            }
        });
    }
});

// Public API
function swiftNodeConfig(addonName, selector, url, folderPicker, opts, tbOpts) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    opts = opts || {};
    tbOpts = tbOpts || {};
    self.viewModel = new swiftFolderPickerViewModel(addonName, url, selector, folderPicker, opts, tbOpts);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    swiftNodeConfig: swiftNodeConfig,
    _swiftNodeConfigViewModel: swiftFolderPickerViewModel
};
