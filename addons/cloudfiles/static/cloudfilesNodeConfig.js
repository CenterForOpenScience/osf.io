'use strict';

var $ = require('jquery');
var ko = require('knockout');
var m = require('mithril');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var $modal = $('#cloudfilesInputCredentials');
var oop = require('js/oop');
var osfHelpers = require('js/osfHelpers');
var OauthAddonFolderPicker = require('js/oauthAddonNodeConfig')._OauthAddonNodeConfigViewModel;
var language = require('js/osfLanguage').Addons.cloudfiles;
var bootbox = require('bootbox');

var FolderPicker = require('js/folderpicker');

var cloudFilesSettings = require('json!./settings.json');

var ViewModel = oop.extend(OauthAddonFolderPicker,{

    constructor: function(addonName, url, selector, folderPicker, opts, tbOpts) {
        var self = this;
        self.super.super.constructor.call(self, addonName, url, selector, folderPicker, tbOpts);
        self.super.construct.call(self, addonName, url, selector, folderPicker, opts, tbOpts);
        // Non-Oauth fields:
        self.username = ko.observable('');
        self.secretKey = ko.observable('');
        self.containerLocations = ko.observable(cloudFilesSettings.containerLocations);
        self.selectedRegion = ko.observable(cloudFilesSettings.containerLocations[0].value);

        self.treebeardOptions = $.extend(
            {},
            OauthAddonFolderPicker.prototype.treebeardOptions,
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
                    return m('i.fa. fa-cube', ' ');
                },
                onPickFolder: function(evt, item) {
                    evt.preventDefault();
                    var name = item.data.path !== '/' ? item.data.path : '/ (Full ' + self.addonName + ')';
                    self.selected({
                        name: name,
                        path: item.data.path,
                        id: item.data.id
                    });
                    return false; // Prevent event propagation
                }
            },
            tbOpts
        );

    },
    clearModal : function() {
        var self = this;
        self.username(null);
        self.secretKey(null);
    },
    connectAccount : function() {
        var self = this;
        return osfHelpers.postJSON(
            self.url,
            ko.toJS({
                secretKey: self.secretKey,
                username: self.username
            })
        ).done(function(response) {
            self.clearModal();
            $modal.modal('hide');
            self.changeMessage('Successfully added Cloud Files credentials.', 'text-success', null, true);
            self.updateAccounts(response);
            self.importAuth();
        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with Cloud Files', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    },
    formatExternalName: function(item) {
        return {
            text: $osf.htmlEscape(item.name) + ' - ' + $osf.htmlEscape(item.profile),
            value: item.id
        };
    },
    activatePicker: function() {
        var self = this;
        var opts = $.extend({}, {
            initialFolderPath: self.folder().path || '',
            // Fetch folders with AJAX
            filesData: self.urls().folders + '?region=' + self.selectedRegion(), // URL for fetching folders
            // Lazy-load each folder's contents
            // Each row stores its url for fetching the folders it contains
            oddEvenClass: {
                odd: 'addon-folderpicker-odd',
                even: 'addon-folderpicker-even'
            },
            multiselect: false,
            allowMove: false,
            ajaxOptions: {
                error: function(xhr, textStatus, error) {
                    self.loading(false);
                    self.changeMessage(self.messages.connectError(), 'text-danger');
                    Raven.captureMessage('Could not GET get ' + self.addonName + ' contents.', {
                        extra: {
                            textStatus: textStatus,
                            error: error
                        }
                    });
                }
            },
            folderPickerOnload: function() {
                // Hide loading indicator
                self.loading(false);
                // Set flag to prevent repeated requests
                self.loadedFolders(true);
            },
            xhrconfig: $osf.setXHRAuthorization,
        }, self.treebeardOptions);
        self.currentDisplay(self.PICKER);
        // Only load folders if they haven't already been requested
        if (!self.loadedFolders()) {
            self.doActivatePicker(opts);
        }
    },
    changeRegion: function(ctrl ,env) {
        this.selectedRegion(env.target.value);
        this.loadedFolders(false);
        this.activatePicker();
    },

    createContainer: function(self, containerName, containerLocation) {
        $osf.block();
        return $osf.postJSON(
            self.urls().createContainer, {
                container_name: containerName,
                container_location: containerLocation
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

        // Generates html options for key-value pairs in BUCKET_LOCATION_MAP
        function generateContainerOptions(locations) {
            var options = '';
            for (var ind in locations) {
                options = options + ['<option value="', locations[ind]['value'], '">', locations[ind]['label'], '</option>', '\n'].join('');
            }
            return options;
        }

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
                                '<div class="form-group"> ' +
                                    '<label class="col-md-4 control-label" for="containerLocation">Container Location</label> ' +
                                    '<div class="col-md-8"> ' +
                                        '<select id="containerLocation" name="containerLocation" class="form-control"> ' +
                                            generateContainerOptions(self.containerLocations()) +
                                        '</select>' +
                                    '</div>' +
                                '</div>' +
                            '</form>' +
                            '<span>For more information on locations, click ' +
                                '<a href="http://help.osf.io/m/addons/l/524149#BucketLocations">here</a>' +
                            '</span>' +
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
                        var containerLocation = $('#containerLocation').val();

                        if (!containerName) {
                            var errorMessage = $('#containerModalErrorMessage');
                            errorMessage.text('Container name cannot be empty');
                            errorMessage[0].classList.add('text-danger');
                            return false;
                        } else {
                            self.createContainer(self, containerName, containerLocation);
                        }
                    }
                }
            }
        });
    }
});

function CloudFilesNodeConfig(selector, url) {
    var self = this;
    self.viewModel = new ViewModel('cloudfiles', url, selector, '#cloudfilesGrid', {});
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = CloudFilesNodeConfig;
