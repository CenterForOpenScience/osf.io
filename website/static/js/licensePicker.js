var $ = require('jquery');
var ko = require('knockout');
require('knockout.validation');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');

var siteLicenses = require('js/licenses');
var licenses = siteLicenses.list;
var DEFAULT_LICENSE = siteLicenses.DEFAULT_LICENSE;
var OTHER_LICENSE = siteLicenses.OTHER_LICENSE;

var template = require('raw!templates/license-picker.html');

/**
 * @class LicensePicker: Knockout.js view model for project license selection
 * 
 * @param {string} saveUrl: url to make save requests to
 * @param {string} saveMethod: HTTP method for save request (one of 'GET', 'POST', 'PUT', 'PATCH')
 * @param {string} saveLicenseKey: key to use for save request payload
 * @param {license} license: optional instantiation license
 * @property {ko.observable<boolean>} previewing:
 * @property {ko.observable<license>} savedLicense:
 * @property {ko.observable<license>} selectedLicense:
 * @property {license[]} licenses: 
 * @property {ko.observable<string>} notification:
 * @property {ko.observable<boolean>} error:
 *
 * @type license
 * @property {string} name: human readable name
 * @property {string} text: full text of license
 * @property {string} id: unique identifier
 **/
var LicensePicker = function(saveUrl, saveMethod, saveLicenseKey, license, readonly) {
    var self = this;

    var user = $osf.currentUser();

    self.saveUrl = saveUrl || '';
    self.saveMethod = saveMethod || 'POST';
    self.saveLicenseKey = saveLicenseKey || 'license';    

    self.previewing = ko.observable(false);

    self.licenses = licenses;

    license = license || DEFAULT_LICENSE;

    self.savedLicense = ko.observable(license);
    self.savedLicenseName = ko.pureComputed(function() {
        return self.savedLicense().name;
    });
    self.savedLicenseId = ko.computed(function() {
        return self.savedLicense().id;
    });

    self.selectedLicense = ko.observable(DEFAULT_LICENSE);
    self.selectedLicenseUrl = ko.pureComputed(function() {
        return self.selectedLicense().url;
    });
    /** ;
     * Needed to track selected/saved license in the list of licenses
     **/     
    self.selectedLicenseId = ko.computed({
        read: function() {
            return self.selectedLicense().id;
        },
        write: function(id) {
            self.selectedLicense(self.licenses.filter(function(l) {
                return l.id === id;
            })[0]);
        }
    });
    self.selectedLicenseId(license.id);

    self.Year = ko.observable(license.Year || new Date().getFullYear()).extend({
        required: true,
        pattern: {
            params: /^\d{4}\s*$/,            
            message: 'Please specify a valid year.'
        },
        max: {
            params: new Date().getFullYear(),
            message: 'Future years are not allowed'
        }
    });
    self['Copyright Holders'] = ko.observable(license['Copyright Holders'] || '').extend({required: true});
    self.dirty = ko.computed(function() {
        var savedLicense = self.savedLicense();
        return self.Year() !== savedLicense.Year || self['Copyright Holders']() !== savedLicense['Copyright Holders'];
    });
    self.properties = ko.computed(function() {
        var props = self.selectedLicense().properties;
        if (props) {
            return $.map(props, function(prop) {
                return {
                    name: prop,
                    value: self[prop]
                };
            });
        }
        return null;
    });
    self.selectedLicenseText = ko.computed(function() {
        return self.selectedLicense().text
            .replace('{{year}}', self.Year())
            .replace('{{copyrightHolders}}', self['Copyright Holders']());
    });

    self.validProps = ko.computed(function() {
        return (!self.properties()) || (self.Year.isValid() && self['Copyright Holders'].isValid());
    });

    self.disableSave = ko.computed(function() {
        return !self.validProps() || !self.dirty() && self.selectedLicenseId() === self.savedLicenseId();
    });

    self.notification = ko.observable();
    var notificationInterval;
    self.notification.subscribe(function(value) {
        if (notificationInterval) {
            window.clearInterval(notificationInterval);
        }
        if (value) {
            notificationInterval = window.setInterval(function() {
                self.notification(null);
            }, 2500);
        }
    });
    self.error = ko.observable(false);
    self.success = ko.computed(function() {
        return !self.error();
    });

    self.allowEdit = ko.pureComputed(function() {
        return user.isAdmin && !readonly;
    });

    self.hideLicensePicker = ko.computed(function() {
        return !user.isAdmin && self.selectedLicenseId() === DEFAULT_LICENSE.id;
    });
};
LicensePicker.prototype.togglePreview = function(labelClicked) {
    var self = this;
    
    if (labelClicked) {
        if (self.allowEdit()) {       
            self.previewing(!self.previewing()); 
        }
    }
    else {
        self.previewing(!self.previewing());
    }
};
LicensePicker.prototype.onSaveSuccess = function(selectedLicense) {
    var self = this;

    self.error(false);
    self.previewing(false);
    self.savedLicense(selectedLicense);
    self.notification('License updated successfully.');
};
LicensePicker.prototype.onSaveFail = function() {
    var self = this;

    self.notification('There was a problem updating your license. Please try again.');
    self.error(true);
};
/**
 * Save the currently selected license, updating the UI on success/fail
 **/
LicensePicker.prototype.save = function() {
    var self = this;

    if (!self.validProps()) {
        return;
    }

    var license = self.selectedLicense();

    var payload = {};
    var selectedLicense = self.selectedLicense();
    selectedLicense.Year = self.Year();
    selectedLicense['Copyright Holders'] = self['Copyright Holders']();

    payload[self.saveLicenseKey] = selectedLicense;
    var save = function() {
        return $.ajax({
            url: self.saveUrl,
            method: self.saveMethod,
            contentType: 'application/json',
            data: JSON.stringify(payload)
        }).done(self.onSaveSuccess.bind(self, selectedLicense)).fail(self.onSaveFail.bind(self));
    };
    if (license.id === OTHER_LICENSE.id) {
        var ret = $.Deferred();
        bootbox.dialog({
            title: 'Please confirm your license selection',
            message: 'You have opted to use your own license. It is your responsiblity to upload and maintain a license file named "license.txt" and to upload that file into the OSF Storage of this project.',
            buttons: {
                cancel: {
                    label: 'Cancel',
                    className: 'btn btn-default'
                },
                main: {
                    label: 'Ok',
                    className: 'btn btn-primary',
                    callback: function(confirmed) {
                        if (confirmed) {
                            save().then(ret.resolve);
                        }
                        else {
                            ret.reject();
                        }
                    }                    
                }
            }
        });
        return ret.promise();
    } else {
        return save();
    }
};

ko.components.register('license-picker', {
    viewModel: {
        createViewModel: function(params, componentInfo) {
            var license = params.license || {};
            if (!Object.keys(license).length) {
                license = null;
            }
            var readonly = params.readonly || false;
            return new LicensePicker(params.saveUrl, params.saveMethod, params.saveLicenseKey, license, readonly);
        }
    },
    template: template
});

module.exports = LicensePicker;
