'use strict';

var $ = require('jquery');
var Cookie = require('js-cookie');

$('#institutional_storage_form').submit(function (e) {
    if ($('#institutional_storage_form')[0].checkValidity()) {
        var selectedProvider = $('input[name=\'options\']:checked').val();
        $('#' + selectedProvider + '_modal').modal('show');
    }
    e.preventDefault();
});

$('#s3_modal input').keyup(function () {
    validateRequiredFields('s3');
});

$('#swift_modal input').keyup(function () {
    validateRequiredFields('swift');
});

$('#owncloud_modal input').keyup(function () {
    validateRequiredFields('owncloud');
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
    if (swift_keystone_version_val === 'v2') {
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
    validateRequiredFields('swift');
});

function test_connection(this_object) {
    var id_of_modal = $(this_object).attr('id')
    var short_name_of_provider = id_of_modal.replace('_connect', '')
    if (short_name_of_provider === 's3') {
        var s3_access_key = $('#s3_access_key').val();
        var s3_secret_key = $('#s3_secret_key').val();
        var s3_bucket = $('#s3_bucket').val();

        var params = {
            's3_access_key': s3_access_key,
            's3_secret_key': s3_secret_key,
            's3_bucket': s3_bucket,
            'provider_short_name': short_name_of_provider,
        };
        ajax_request(params, short_name_of_provider);

    }

}

function ajax_request(params, short_name_of_provider) {
    var csrftoken = Cookie.get('admin-csrf');

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            }
        }
    });
    var request = $.ajax({
        url: '../test_connection',
        type: 'POST',
        data: JSON.stringify(params),
        contentType: 'application/json; charset=utf-8',
        custom: short_name_of_provider,
    });

    request.done(function (data, xhr) {
        test_connection_succeed(this.custom, data);
    });

    request.fail(function (jqXHR) {
        test_connection_failed(this.custom, jqXHR.responseJSON.message);
    });
}

$('.test-connection').click(function () {
    test_connection(this);
});


function test_connection_succeed(id, data) {
    $('#' + id + '_save').attr('disabled', false);
    $('#' + id + '_save').removeClass('btn-default').addClass('btn-success ');
    $('#' + id + '_connect').removeClass('btn-success').addClass('btn-default ');
    $('#' + id + '_message').html(data.message);
    if (!$('#' + id + '_message').hasClass('text-success')) {
        $('#' + id + '_message').addClass('text-success ');
        $('#' + id + '_message').removeClass('text-danger ');
    }
}

function test_connection_failed(id, message) {
    $('#' + id + '_message').html(message);
    $('#' + id + '_save').attr('disabled', true);
    $('#' + id + '_save').removeClass('btn-success').addClass('btn-default ');
    $('#' + id + '_connect').removeClass('btn-default').addClass('btn-success ');
    if (!$('#' + id + '_message').hasClass('text-danger')) {
        $('#' + id + '_message').addClass('text-danger ');
        $('#' + id + '_message').removeClass('text-success ');
    }
}