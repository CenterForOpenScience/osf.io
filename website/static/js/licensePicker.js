var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var licenses = require('list-of-licenses');

var $osf = require('js/osfHelpers');

var template = require('raw!templates/license-picker.html');

var DEFAULT_LICENSE = {
    id: 'NONE',
    name: 'None',
    text: 'Copyright [year] [fullname]'
};
var OTHER_LICENSE = {
    id: 'OTHER',
    name: 'Other',
    text: 'Please see the "license.txt" uploaded in this project\'s OSF Storage'
};

/**
 * @class LicensePicker: Knockout.js view model for project license selection
 * 
 * @param {string} saveUrl: url to make save requests to
 * @param {string} saveMethod: HTTP method for save request (one of 'GET', 'POST', 'PUT', 'PATCH')
 * @param {string} saveLicenseKey: key to use for save request payload
 * @param {license} license: optional instantiation license
 * @property {ko.observable<boolean>} editing: 
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
var LicensePicker = function(saveUrl, saveMethod, saveLicenseKey, license) {
    var self = this;

    self.saveUrl = saveUrl || '';
    self.saveMethod = saveMethod || 'POST';
    self.saveLicenseKey = saveLicenseKey || 'license';

    self.editing = ko.observable(false);
    self.previewing = ko.observable(false);

    self.licenses = $.map(licenses, function(value, key) {
        value.id = key;
        return value;
    });
    self.licenses.unshift(DEFAULT_LICENSE);
    self.licenses.push(OTHER_LICENSE);

    self.savedLicense = ko.observable(license || DEFAULT_LICENSE);
    self.savedLicenseName = ko.pureComputed(function() {
        return self.savedLicense().name;
    });

    self.selectedLicense = ko.observable(license || DEFAULT_LICENSE);
    self.selectedLicenseText = ko.pureComputed(function() {
        return self.selectedLicense().text;
    });
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

    self.disableSave = ko.computed(function() {
        return self.selectedLicense().id === self.savedLicense().id;
    });

    self.showPreview = ko.computed(function() {
        return self.previewing() || self.editing();
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
};
LicensePicker.prototype.togglePreview = function() {
    var self = this;

    self.previewing(!self.previewing());
};
LicensePicker.prototype.onSaveSuccess = function(selectedLicense) {
    var self = this;

    self.error(false);
    self.editing(false);
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

    var license = self.selectedLicense();

    var payload = {};
    var selectedLicense = self.selectedLicense();
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
        bootbox.confirm(
            'You have opted to use your own license. It is your responsiblity to upload and maintain a license file named "license.txt" and to upload that file into the OSF Storage of this project.',
            function(confirmed) {
                if (confirmed) {
                    save().then(ret.resolve);
                }
                else {
                    ret.reject();
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
            return new LicensePicker(params.saveUrl, params.saveMethod, params.saveLicenseKey, license);
        }
    },
    template: template
});

module.exports = LicensePicker;
