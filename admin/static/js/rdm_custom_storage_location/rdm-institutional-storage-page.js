'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Cookie = require('js-cookie');

$('#institutional_storage_form').submit(function (e) {
    if ($('#institutional_storage_form')[0].checkValidity()) {
        var selectedProvider = $('input[name=\'options\']:checked').val();
        var showModal = function () {
            $('#' + selectedProvider + '_modal').modal('show');
        };
        if (selectedProvider === 'osfstorage') {
            showModal();
        } else {
            $osf.confirmDangerousAction({
                title: 'Are you sure you want to change institutional storage?',
                message: '<p>The previous storage will no longer be available to all contributors on the project.</p>',
                callback: showModal,
                buttons: {
                    success: {
                        label: 'Change'
                    }
                }
            });
        }
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

$('#nextcloud_modal input').keyup(function () {
    validateRequiredFields('nextcloud');
});

function validateRequiredFields(providerShortName) {
    // Check if all the inputs are filled, so we can enable the connect button
    var allFilled = $('#' + providerShortName + '_modal [required]').toArray().reduce(function (accumulator, current) {
        return accumulator && current.value.length > 0;
    }, true);
    $('#' + providerShortName + '_connect').attr('disabled', !allFilled);
}

$('#swift_auth_version').change(function () {
    var swiftKeystoneVersion = $(this).val();
    if (swiftKeystoneVersion === '2') {
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

function testConnection(thisObject) {
    var modalId = $(thisObject).attr('id');
    var providerShortName = modalId.replace('_connect', '');
    var params = {
        'provider_short_name': providerShortName
    };

    switch (providerShortName) {
        case 's3':
            params.s3_access_key = $('#s3_access_key').val();
            params.s3_secret_key = $('#s3_secret_key').val();
            params.s3_bucket = $('#s3_bucket').val();
            break;
        case 'owncloud':
            params.owncloud_host = $('#owncloud_host').val();
            params.owncloud_folder = $('#owncloud_folder').val();
            params.owncloud_username = $('#owncloud_username').val();
            params.owncloud_password = $('#owncloud_password').val();
            break;
        case 'swift':
            getParameters(params);
        case 'nextcloud':
            getParameters(params);
    }

    ajaxRequest(params, providerShortName);
}

function ajaxRequest(params, providerShortName) {
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
        custom: providerShortName,
    });

    request.done(function (data) {
        testConnectionSucceed(this.custom, data);
    });

    request.fail(function (jqXHR) {
        testConnectionFailed(this.custom, jqXHR.responseJSON.message);
    });
}

$('.test-connection').click(function () {
    testConnection(this);
});


function testConnectionSucceed(id, data) {
    $('#' + id + '_save').attr('disabled', false);
    $('#' + id + '_save').removeClass('btn-default').addClass('btn-success ');
    $('#' + id + '_connect').removeClass('btn-success').addClass('btn-default ');
    $('#' + id + '_message').html(data.message);
    if (!$('#' + id + '_message').hasClass('text-success')) {
        $('#' + id + '_message').addClass('text-success ');
        $('#' + id + '_message').removeClass('text-danger ');
    }
}

function testConnectionFailed(id, message) {
    $('#' + id + '_message').html(message);
    $('#' + id + '_save').attr('disabled', true);
    $('#' + id + '_save').removeClass('btn-success').addClass('btn-default ');
    $('#' + id + '_connect').removeClass('btn-default').addClass('btn-success ');
    if (!$('#' + id + '_message').hasClass('text-danger')) {
        $('#' + id + '_message').addClass('text-danger ');
        $('#' + id + '_message').removeClass('text-success ');
    }
}

function getParameters(params) {
    var providerClass = params.provider_short_name + '-params';
    var allParameters = $('.' + providerClass);
    $.each(allParameters, function (key, value) {
        if (!value.disabled) {
            params[value.id] = value.value;
        }
    });
}
