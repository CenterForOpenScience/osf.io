'use strict';

var $ = require('jquery');
var ko = require('knockout');
var m = require('mithril');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var oop = require('js/oop');

var s3Settings = require('json!./settings.json');

var OauthAddonFolderPicker = require('js/oauthAddonNodeConfig')._OauthAddonNodeConfigViewModel;

var s3FolderPickerViewModel = oop.extend(OauthAddonFolderPicker, {
    bucketLocations: s3Settings.bucketLocations,

    constructor: function(addonName, url, selector, folderPicker, opts, tbOpts) {
        var self = this;
        self.super.constructor(addonName, url, selector, folderPicker, tbOpts);
        // Non-OAuth fields
        self.accessKey = ko.observable('');
        self.secretKey = ko.observable('');
        // Treebeard config
        self.treebeardOptions = $.extend(
            {},
            OauthAddonFolderPicker.prototype.treebeardOptions,
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
        $osf.block();

        return $osf.postJSON(
            self.urls().create, {
                secret_key: self.secretKey(),
                access_key: self.accessKey()
            }
        ).done(function(response) {
            $osf.unblock();
            self.clearModal();
            $('#s3InputCredentials').modal('hide');
            self.changeMessage('Successfully added S3 credentials.', 'text-success', null, true);
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
            Raven.captureMessage('Could not add S3 credentials', {
                extra: {
                    url: self.urls().importAuth,
                    textStatus: status,
                    error: error
                }
            });
        });
    },
    /**
     * Tests if the given string is a valid Amazon S3 bucket name.  Supports two modes: strict and lax.
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

    /** Reset all fields from S3 credentials input modal */
    clearModal: function() {
        var self = this;
        self.message('');
        self.messageClass('text-info');
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

    openCreateBucket: function() {
        var self = this;

        // Generates html options for key-value pairs in BUCKET_LOCATION_MAP
        function generateBucketOptions(locations) {
            var options = '';
            for (var location in locations) {
                if (self.bucketLocations.hasOwnProperty(location)) {
                    options = options + ['<option value="', location, '">', $osf.htmlEscape(locations[location]), '</option>', '\n'].join('');
                }
            }
            return options;
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
                                        '<select id="bucketLocation" name="bucketLocation" class="form-control"> ' +
                                            generateBucketOptions(self.bucketLocations) +
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
                                message: 'Amazon S3 buckets can contain lowercase letters, numbers, and hyphens separated by' +
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
function s3NodeConfig(addonName, selector, url, folderPicker, opts, tbOpts) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    opts = opts || {};
    tbOpts = tbOpts || {};
    self.viewModel = new s3FolderPickerViewModel(addonName, url, selector, folderPicker, opts, tbOpts);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    s3NodeConfig: s3NodeConfig,
    _s3NodeConfigViewModel: s3FolderPickerViewModel
};
