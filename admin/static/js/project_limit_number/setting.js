'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var _ = require('js/rdmGettext')._;
var Cookie = require('js-cookie');

function handleAjaxRequestFailure(jqXHR) {
    switch (jqXHR.status) {
        case 401:
            // Remove cookie then redirect to login page
            Cookie.remove('admin');
            Cookie.remove('admin-csrf');
            window.location.href = '/account/login';
            break;
        case 403:
            // Redirect to 403 page
            window.location.href = '/403';
            break;
        case 404:
            // Redirect to 404 page
            window.location.href = '/404';
            break;
        case 500:
            // If jqXHR response is text/plain, replace html body with error message
            if (!jqXHR.responseJSON && !!jqXHR.responseText) {
                var data = jqXHR.responseText;
                if (data.includes('<html>')) {
                    data = $(jqXHR.responseText).find('body').html();
                }
                $('body').html(data);
                break;
            } else {
                // Otherwise, display error message
                $osf.growl(_('Error'), _('An error occurred. Please try again later.'), 'danger', 5000);
            }
            break;
        default:
            // Display error message
            var data = jqXHR.responseJSON;
            if (data && data['error_message']) {
                // Convert message from snake_case to camelCase
                if (data['error_message'].includes('_')) {
                    data['error_message'] = "The " + data['error_message'].replace('_', ' ');
                }
                $osf.growl(_('Error'), _(data['error_message']), 'danger', 5000);
            } else {
                $osf.growl(_('Error'), _('An error occurred. Please try again later.'), 'danger', 5000);
            }
            break;
    }
}

function setInvalidMessageForSettingName(event) {
    var element = event.target;
    element.setCustomValidity('');
    if (!!element.validity.valueMissing) {
        element.setCustomValidity(_('The setting name is required.'));
    } else if (!!element.validity.tooLong) {
        element.setCustomValidity(_('Length of setting name > 255 characters.'));
    }
}

function setInvalidMessageForAttributeValue(event) {
    var element = event.target;
    element.setCustomValidity('');
    if (!!element.validity.valueMissing) {
        element.setCustomValidity(_('The attribute value is required.'));
    }
}

$(document).ready(function() {
    $('#setting_name_id').on('invalid', setInvalidMessageForSettingName);
    $('input[name="attribute_value_input"]').on('invalid', setInvalidMessageForAttributeValue);
})

// Expose functions to the global scope
window.handleAjaxRequestFailure = handleAjaxRequestFailure;
