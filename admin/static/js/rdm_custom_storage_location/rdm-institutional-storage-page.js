'use strict';

var $ = require('jquery');

$("#institutional_storage_form").submit(function (e) {
    if ($('#institutional_storage_form')[0].checkValidity()) {
        var selectedProvider = $('input[name=\'options\']:checked').val();
        $('#' + selectedProvider + '_modal').modal('show');
    }
    e.preventDefault();
});

$('#s3_modal input').keyup(function () {
    validateRequiredFields('s3')
});

$('#swift_modal input').keyup(function () {
    validateRequiredFields('swift')
});

function validateRequiredFields(providerShortName) {
    // Check if all the inputs are filled, so we can enable the connect button
    var allFilled = $('#' + providerShortName + '_modal [required]').toArray().reduce(function (accumulator, current) {
        return accumulator && current.value.length > 0;
    }, true);
    $('#' + providerShortName + '_connect').attr('disabled', !allFilled);
}

$('#swift_keytone_versionSelect').change(function () {
    var swift_keystone_version_val = $(this).val();
    if (swift_keystone_version_val == 'v2') {
        $('#swift_project_domain_name').attr('disabled', true);
        $('#swift_user_domain_name').attr('disabled', true);
        $('#swift_project_domain_name').attr('required', false);
        $('#swift_user_domain_name').attr('required', false);
    } else {
        $('#swift_project_domain_name').attr('disabled', false);
        $('#swift_user_domain_name').attr('disabled', false);
        $('#swift_project_domain_name').attr('required', true);
        $('#swift_user_domain_name').attr('required', true);
    }
    validateRequiredFields('swift')
});
