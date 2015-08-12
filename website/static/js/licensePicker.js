var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');

require('js/overflowBox.js');

var template = require('raw!templates/license-picker.html');

var defaultLicense = {
    id: 'DEFAULT',
    name: 'Default License',
    text: 'TODO'
};
var otherLicense = {
    id: 'OTHER',
    name: 'Other',
    text: 'Please see the "license.txt" uploaded in this project\'s OSF Storage'
};

var LicensePicker = function(saveUrl, saveMethod, license) {
    var self = this;

    self.saveUrl = saveUrl || '';
    self.saveMethod = saveMethod || 'PUT';

    self.editing = ko.observable(false);
    self.previewing = ko.observable(false);

    self.licenses = $.map(require('list-of-licenses'), function(value, key) {
        value.id = key;
        return value;
    });
    self.licenses.unshift(defaultLicense);
    self.licenses.push(otherLicense);

    self.savedLicense = ko.observable(license || defaultLicense);
    self.savedLicenseName = ko.pureComputed(function() {
        return self.savedLicense().name;
    });
    self.selectedLicense = ko.observable(license || defaultLicense);
    self.selectedLicenseName = ko.pureComputed(function() {
        return self.selectedLicense().name;
    });
    self.selectedLicenseText = ko.pureComputed(function() {
        return self.selectedLicense().text;
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
            }, 3000);
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
LicensePicker.prototype.save = function() {
    var self = this;

    var license = self.selectedLicense();

    var save = function() {
        $.ajax({
            url: self.saveUrl,
            method: self.saveMethod,
            contentType: 'application/json',
            data: JSON.stringify({
                node_license: self.selectedLicense()
            })
        }).done(function(response) {
            self.error(false);
            self.editing(false);
            self.previewing(false);
            self.savedLicense(response.updated_fields.license);
            self.notification('License updated successfully.');
        }).fail(function() {
            self.notification('There was a problem updating your license. Please try again.');
            self.error(true);
        });
    };
    if (license.id === otherLicense.id) {
        bootbox.confirm(
            'You have opted to use your own license. It is your responsiblity to upload and maintain a license file named "license.txt" and to upload that file into the OSF Storage of this project',
            function(confirmed) {
                if (confirmed) {
                    save();
                }
            });
    } else {
        save();
    }
};

ko.components.register('license-picker', {
    viewModel: {
        createViewModel: function(params, componentInfo) {
            return new LicensePicker(params.saveUrl, params.saveMethod, params.license);
        }
    },
    template: template
});

module.exports = LicensePicker;
