var $ = require('jquery');
var ko = require('knockout');
require('knockout.validation');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var ChangeMessageMixin = require('js/changeMessage');

var siteLicenses = require('js/licenses');
var licenses = siteLicenses.list;
var DEFAULT_LICENSE = siteLicenses.DEFAULT_LICENSE;
var OTHER_LICENSE = siteLicenses.OTHER_LICENSE;
var licenseGroups = siteLicenses.groups;

var LICENSE_PROPERTIES = {
    'year': 'Year',
    'copyrightHolders': 'Copyright Holders'
};

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
 *
 * @type license
 * @property {string} name: human readable name
 * @property {string} text: full text of license
 * @property {string} id: unique identifier
 **/
var LicensePicker = oop.extend(ChangeMessageMixin, {
    constructor: function(saveUrl, saveMethod, saveLicenseKey, license, readonly) {
        this.super.constructor.call(this);

        var self = this;

        var user = $osf.currentUser();

        self.saveUrl = saveUrl || '';
        self.saveMethod = saveMethod || 'POST';
        self.saveLicenseKey = saveLicenseKey || 'license';

        self.previewing = ko.observable(false);

        self.licenses = licenses;
        self.licenseGroups = licenseGroups;

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
        /**
         * Needed to track selected/saved license in the list of licenses
         **/
        self.selectedLicenseId = ko.computed({
            read: function() {
                return self.selectedLicense().id;
            },
            write: function(id) {
                var selected  = self.licenses.filter(function(l) {
                    return l.id === id;
                })[0];
                if (selected) {
                    self.selectedLicense(selected);
                }
            }
        });
        self.selectedLicenseId(license.id);


        self.hideValidation = ko.computed(function() {
            return self.selectedLicenseId() === DEFAULT_LICENSE.id;
        });
        self.year = ko.observable(license.year || new Date().getFullYear()).extend({
            required: true,
            pattern: {
                params: /^\d{4}\s*$/,
                message: 'Please specify a valid year.'
            },
            max: {
                params: new Date().getFullYear(),
                message: 'Future years are not allowed.'
            }
        });
        self.copyrightHolders = ko.observable((license.copyright_holders || []).join(', ')).extend({
            required: true
        });

        self.dirty = ko.computed(function() {
            var savedLicense = self.savedLicense();
            return self.year() !== savedLicense.year || self.copyrightHolders() !== savedLicense.copyrightHolders;
        });
        self.properties = ko.computed(function() {
            var props = self.selectedLicense().properties;
            if (props) {
                return $.map(props, function(prop) {
                    return {
                        name: LICENSE_PROPERTIES[prop],
                        value: self[prop]
                    };
                });
            }
            return null;
        });
        self.selectedLicenseText = ko.computed(function() {
            if (self.selectedLicense().text) {
                return self.selectedLicense().text
                    .replace('{{year}}', self.year())
                    .replace('{{copyrightHolders}}', self.copyrightHolders());
            } else{
                return '';
            }
        });

        self.validProps = ko.computed(function() {
            var props = self.properties();
            if (props) {
                var valid = true;
                $.each(props, function(i, prop) {
                    valid = valid && prop.value.isValid();
                });
                return valid;
            }
            else {
                return true;
            }
        });

        self.selectedLicense.subscribe(function() {
            var group = ko.validation.group(
                $.map(self.properties() || [], function(p) { return p.value; })
            );
            group.showAllMessages();
        });

        self.disableSave = ko.computed(function() {
            return (self.selectedLicenseId() !== DEFAULT_LICENSE.id) && (!self.validProps() || !self.dirty() && self.selectedLicenseId() === self.savedLicenseId());
        });

        self.allowEdit = ko.pureComputed(function() {
            return user.isAdmin && !readonly;
        });

        self.hideLicensePicker = ko.computed(function() {
            return !user.isAdmin && self.selectedLicenseId() === DEFAULT_LICENSE.id;
        });
    },
    togglePreview: function(labelClicked) {
        var self = this;

        if (labelClicked) {
            if (self.allowEdit()) {
                self.previewing(!self.previewing());
            }
        } else {
            self.previewing(!self.previewing());
        }
    },
    onSaveSuccess: function(selectedLicense) {
        var self = this;

        self.previewing(false);
        self.savedLicense(selectedLicense);
        self.changeMessage('License updated successfully.', 'text-success', 2500);
    },
    onSaveFail: function(xhr, status, error) {
        var self = this;

        self.changeMessage('There was a problem updating your license. Please try again.', 'text-danger', 2500);

        Raven.captureMessage('Error fetching user profile', {
            url: self.saveUrl,
            status: status,
            error: error
        });
    },
    /**
     * Save the currently selected license, updating the UI on success/fail
     **/
    save: function() {
        var self = this;

        if (self.disableSave()) {
            return;
        }

        var license = self.selectedLicense();

        var payload = {};
        var selectedLicense = self.selectedLicense();
        var year = self.year();
        var copyrightHolders = $.map(self.copyrightHolders().split(','), $.trim);

        payload[self.saveLicenseKey] = {
            id: selectedLicense.id,
            name: selectedLicense.name,
            copyright_holders: copyrightHolders,
            year: year
        };
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
                title: 'Your Own License',
                message: 'You have opted to use your own license. Please upload a license file named "license.txt" into the OSF Storage of this project.',
                buttons: {
                    cancel: {
                        label: 'Cancel',
                        className: 'btn btn-default'
                    },
                    main: {
                        label: 'Add license',
                        className: 'btn btn-primary',
                        callback: function(confirmed) {
                            if (confirmed) {
                                save().then(ret.resolve);
                            } else {
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
    }
});

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
