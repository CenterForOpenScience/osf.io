'use strict';

var $ = require('jquery');
var ko = require('knockout');
var m = require('mithril');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var oop = require('js/oop');

var s3compatb3b3Settings = require('json-loader!./settings.json');

var OauthAddonFolderPicker = require('js/oauthAddonNodeConfig')._OauthAddonNodeConfigViewModel;

var s3compatb3b3FolderPickerViewModel = oop.extend(OauthAddonFolderPicker, {
    constructor: function(addonName, url, selector, folderPicker, opts, tbOpts) {
        var self = this;
        // TODO: [OSF-7069]
        self.super.super.constructor.call(self, addonName, url, selector, folderPicker, tbOpts);
        self.super.construct.call(self, addonName, url, selector, folderPicker, opts, tbOpts);
        // Non-OAuth fields
        self.availableServices = ko.observableArray(s3compatb3b3Settings['availableServices']);
        self.selectedService = ko.observable(s3compatb3b3Settings['availableServices'][0]);
        self.hostTemplate = ko.observable(s3compatb3Settings['hostTemplate'];
        self.namespaceIndex = ko.observable(s3compatb3Settings['namespaceIndex'];
        self.regionIndex = ko.observable(s3compatb3Settings['regionIndex'];
        self.namespace = ko.observable('');
        self.region = ko.observable('');
        //self.host = ko.observable(s3compatb3Settings['hostTemplate'];
        self.host = ko.computed(function() {
            let dc = this.hostTemplate().split('.');
            dc[this.namespaceIndex()] = this.namespace();
            dc[this.regionIndex()] = this.region();
            return dc.join('.');
        }, self);
        self.accessKey = ko.observable('');
        self.secretKey = ko.observable('');
        // Treebeard config
        self.treebeardOptions = $.extend(
            {},
            self.treebeardOptions,
            {   // TreeBeard Options
                columnTitles: function() {
                    return [{
                        title: 'Buckets',
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

        // Description about an attached service
        self.attachedService = null;
        self.nodeHasAuth.subscribe(function(newValue) {
            if (newValue && self.urls().length > 0) {
                self.fetchAttachedService(self);
            }
        });
        self.urls.subscribe(function(newValue) {
            if (self.nodeHasAuth()) {
                self.fetchAttachedService(self);
            }
        });
    },

    connectAccount: function() {
        var self = this;
        if( !self.accessKey() && !self.secretKey() ){
            self.changeMessage('Please enter both an API access key and secret key.', 'text-danger');
            return;
        }

        if (!self.accessKey() ){
            self.changeMessage('Please enter an API access key.', 'text-danger');
            return;
        }

        if (!self.secretKey() ){
            self.changeMessage('Please enter an API secret key.', 'text-danger');
            return;
        }
        if( !self.namespace() && !self.region() ){
            self.changeMessage('Please enter both an namespace and region.', 'text-danger');
            return;
        }

        if (!self.namespace() ){
            self.changeMessage('Please enter an namespace.', 'text-danger');
            return;
        }

        if (!self.region() ){
            self.changeMessage('Please enter an region.', 'text-danger');
            return;
        }
        $osf.block();

        return $osf.postJSON(
            self.urls().create, {
                host: self.host(),
                secret_key: self.secretKey(),
                access_key: self.accessKey()
            }
        ).done(function(response) {
            $osf.unblock();
            self.clearModal();
            $('#s3compatb3b3InputCredentials').modal('hide');
            self.changeMessage('Successfully added S3 Compatible Storage credentials.', 'text-success', null, true);
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
            Raven.captureMessage('Could not add S3 Compatible Storage credentials', {
                extra: {
                    url: self.urls().importAuth,
                    textStatus: status,
                    error: error
                }
            });
        });
    },
    /**
     * Tests if the given string is a valid S3 Compatible Storage bucket name.  Supports two modes: strict and lax.
     * Strict is for bucket creation and follows the guidelines at:
     *
     *   http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html#bucketnamingrules
     *
     * However, the US East (N. Virginia) region currently permits much laxer naming rules.  The S3
     * docs claim this will be changed at some point, but to support our user's already existing
     * buckets, we provide the lax mode checking.
     *
     * Strict checking is the default.
     *
     * @param {String} bucketName user-provided name of bucket to validate
     * @param {Boolean} laxChecking whether to use the more permissive validation
     */
    isValidBucketName: function(bucketName, laxChecking) {
        if (laxChecking === true) {
            return /^[a-zA-Z0-9.\-_]{1,255}$/.test(bucketName);
        }
        var label = '[a-z0-9]+(?:[a-z0-9\-]*[a-z0-9])?';
        var strictBucketName = new RegExp('^' + label + '(?:\\.' + label + ')*$');
        var isIpAddress = /^[0-9]+(?:\.[0-9]+){3}$/;
        return bucketName.length >= 3 && bucketName.length <= 63 &&
            strictBucketName.test(bucketName) && !isIpAddress.test(bucketName);
    },

    /** Reset all fields from S3 Compatible Storage credentials input modal */
    clearModal: function() {
        var self = this;
        self.message('');
        self.messageClass('text-info');
        self.selectedService(s3compatb3b3Settings['availableServices'][0]);
        self.secretKey(null);
        self.accessKey(null);
    },

    createBucket: function(self, bucketName, bucketLocation) {
        $osf.block();
        bucketName = bucketName.toLowerCase();
        return $osf.postJSON(
            self.urls().createBucket, {
                bucket_name: bucketName,
                bucket_location: bucketLocation
            }
        ).done(function(response) {
            $osf.unblock();
            self.loadedFolders(false);
            self.activatePicker();
            var msg = 'Successfully created bucket "' + $osf.htmlEscape(bucketName) + '". You can now select it from the list.';
            var msgType = 'text-success';
            self.changeMessage(msg, msgType, null, true);
        }).fail(function(xhr) {
            var resp = JSON.parse(xhr.responseText);
            var message = resp.message;
            var title = resp.title || 'Problem creating bucket';
            $osf.unblock();
            if (!message) {
                message = 'Looks like that name is taken. Try another name?';
            }
            bootbox.confirm({
                title: $osf.htmlEscape(title),
                message: $osf.htmlEscape(message),
                callback: function(result) {
                    if (result) {
                        self.openCreateBucket();
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

    fetchAttachedService: function(self) {
        var url = self.urls().attachedService;
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
            var targetServices = self.availableServices().filter(function(service) {
              return service.host == data.host;
            });
            self.attachedService = targetServices[0];
        }).fail(function(xhr, status, error) {
          Raven.captureMessage('Error while retrieving addon info', {
              extra: {
                  url: url,
                  status: status,
                  error: error
              }
          });
        });
    },

    openCreateBucket: function() {
        var self = this;

        // Generates html options for key-value pairs in BUCKET_LOCATION_MAP
        function generateBucketOptions() {
            if (self.attachedService == null || (! self.attachedService.bucketLocations)) {
                return '<option value="">(Default Location)</option>';
            }
            var options = '';
            var locations = self.attachedService.bucketLocations;
            var names = new Array();
            for (var location in locations) {
                if (locations.hasOwnProperty(location)) {
                    var name = locations[location]['name'];
                    if (names.indexOf(name) < 0) {
                        options = options + ['<option value="', location, '">', $osf.htmlEscape(name), '</option>', '\n'].join('');
                        names.push(name);
                    }
                }
            }
            return options;
        }

        function generateBucketSelector() {
          return '<select id="bucketLocation" name="bucketLocation" class="form-control"> ' +
                      generateBucketOptions() +
                 '</select>';
        }

        bootbox.dialog({
            title: 'Create a new bucket',
            message:
                    '<div class="row"> ' +
                        '<div class="col-md-12"> ' +
                            '<form class="form-horizontal" onsubmit="return false"> ' +
                                '<div class="form-group"> ' +
                                    '<label class="col-md-4 control-label" for="bucketName">Bucket Name</label> ' +
                                    '<div class="col-md-8"> ' +
                                        '<input id="bucketName" name="bucketName" type="text" placeholder="Enter bucket name" class="form-control" autofocus> ' +
                                        '<div>' +
                                            '<span id="bucketModalErrorMessage" ></span>' +
                                        '</div>'+
                                    '</div>' +
                                '</div>' +
                                '<div class="form-group"> ' +
                                    '<label class="col-md-4 control-label" for="bucketLocation">Bucket Location</label> ' +
                                    '<div class="col-md-8"> ' +
                                        generateBucketSelector() +
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
                        var bucketName = $('#bucketName').val();
                        var bucketLocation = $('#bucketLocation').val();

                        if (!bucketName) {
                            var errorMessage = $('#bucketModalErrorMessage');
                            errorMessage.text('Bucket name cannot be empty');
                            errorMessage[0].classList.add('text-danger');
                            return false;
                        } else if (!self.isValidBucketName(bucketName, false)) {
                            bootbox.confirm({
                                title: 'Invalid bucket name',
                                message: 'S3 Compatible Storage buckets can contain lowercase letters, numbers, and hyphens separated by' +
                                ' periods.  Please try another name.',
                                callback: function (result) {
                                    if (result) {
                                        self.openCreateBucket();
                                    }
                                },
                                buttons: {
                                    confirm: {
                                        label: 'Try again'
                                    }
                                }
                            });
                        } else {
                            self.createBucket(self, bucketName, bucketLocation);
                        }
                    }
                }
            }
        });
    }
});

// Public API
function s3compatb3NodeConfig(addonName, selector, url, folderPicker, opts, tbOpts) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    opts = opts || {};
    tbOpts = tbOpts || {};
    self.viewModel = new s3compatb3FolderPickerViewModel(addonName, url, selector, folderPicker, opts, tbOpts);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    s3compatb3NodeConfig: s3compatb3NodeConfig,
    _s3compatb3NodeConfigViewModel: s3compatb3FolderPickerViewModel
};
