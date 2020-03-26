'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Cookie = require('js-cookie');

var _ = require('js/rdmGettext')._;
var agh = require('agh.sprintf');

$('[name=options]').change(function () {
    $('#storage_name').attr('disabled', this.value === 'osfstorage');
});

$('.modal').on('hidden.bs.modal', function (e) {
    $('body').css('overflow', 'auto');
});

$('#institutional_storage_form').submit(function (e) {
    if ($('#institutional_storage_form')[0].checkValidity()) {
        var selectedProvider = $('input[name=\'options\']:checked').val();
        var showModal = function () {
            $('#' + selectedProvider + '_modal').modal('show');
            $('body').css('overflow', 'hidden');
            $('.modal').css('overflow', 'auto');
            validateRequiredFields(selectedProvider);
        };
        if (selectedProvider === 'osfstorage' && $('[checked]').val() === 'osfstorage') {
            showModal();
        } else {
            $osf.confirmDangerousAction({
                title: _('Are you sure you want to change institutional storage?'),
                message: _('<p>The previous storage will no longer be available to all contributors on the project.</p>'),
                callback: showModal,
                buttons: {
                    success: {
                        label: _('Change')
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

$('#s3_modal input').on('paste', function(e) {
    validateRequiredFields('s3');
});

$('#s3compat_modal input').keyup(function () {
    validateRequiredFields('s3compat');
});

$('#s3compat_modal input').on('paste', function(e) {
    validateRequiredFields('s3compat');
});

$('#swift_modal input').keyup(function () {
    validateRequiredFields('swift');
});

$('#swift_modal input').on('paste', function(e) {
    validateRequiredFields('swift');
});

$('#owncloud_modal input').keyup(function () {
    validateRequiredFields('owncloud');
});

$('#owncloud_modal input').on('paste', function(e) {
    validateRequiredFields('owncloud');
});

$('#nextcloud_modal input').keyup(function () {
    validateRequiredFields('nextcloud');
});

$('#nextcloud_modal input').on('paste', function(e) {
    validateRequiredFields('nextcloud');
});

$('#googledrive_modal input').keyup(function () {
    authSaveButtonState('googledrive');
});

$('#googledrive_modal input').on('paste', function(e) {
    authSaveButtonState('googledrive');
});

$('#box_modal input').keyup(function () {
    authSaveButtonState('box');
});

$('#box_modal input').on('paste', function(e) {
    authSaveButtonState('box');
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

$('.test-connection').click(function () {
    buttonClicked(this, 'test_connection');
});

$('.save-credentials').click(function () {
    buttonClicked(this, 'save_credentials');
});

function buttonClicked(button, route) {
    var action = {
        'test_connection': 'connect',
        'save_credentials': 'save',
    };

    var providerShortName = $(button).attr('id').replace('_' + action[route], '');
    var params = {
        'provider_short_name': providerShortName
    };
    getParameters(params);
    ajaxRequest(params, providerShortName, route);
}

function ajaxRequest(params, providerShortName, route) {
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
    $.ajax({
        url: '../' + route + '/',
        type: 'POST',
        data: JSON.stringify(params),
        contentType: 'application/json; charset=utf-8',
        custom: providerShortName,
        timeout: 30000,
        success: function (data) {
            afterRequest[route].success(this.custom, data);
        },
        error: function (jqXHR) {
            if(jqXHR.responseJSON != null && ('message' in jqXHR.responseJSON)){
                afterRequest[route].fail(this.custom, jqXHR.responseJSON.message);
            }else{
                afterRequest[route].fail(this.custom, _('Some errors occurred'));
            }
        }
    });
}

var afterRequest = {
    'test_connection': {
        'success': function (id, data) {
            $('#' + id + '_save').attr('disabled', false);
            $('#' + id + '_save').removeClass('btn-default').addClass('btn-success');
            $('#' + id + '_connect').removeClass('btn-success').addClass('btn-default');
            $('#' + id + '_message').html(data.message);
            if (!$('#' + id + '_message').hasClass('text-success')) {
                $('#' + id + '_message').addClass('text-success');
                $('#' + id + '_message').removeClass('text-danger');
            }
        },
        'fail': function (id, message) {
            $('#' + id + '_message').html(message);
            $('#' + id + '_save').attr('disabled', true);
            $('#' + id + '_save').removeClass('btn-success').addClass('btn-default');
            $('#' + id + '_connect').removeClass('btn-default').addClass('btn-success');
            if (!$('#' + id + '_message').hasClass('text-danger')) {
                $('#' + id + '_message').addClass('text-danger');
                $('#' + id + '_message').removeClass('text-success');
            }
        }
    },
    'save_credentials': {
        'success': function (id, data) {
            $('#' + id + '_message').html(data.message);
            $('.modal').modal('hide');
            $('#' + id + '_message').addClass('text-success');
            $('#' + id + '_message').removeClass('text-danger');
            $osf.growl('Success', _('Institutional Storage set successfully'), 'success');
            location.reload(true);
        },
        'fail': function (id, message) {
            $('#' + id + '_message').html(message);
            $('#' + id + '_save').attr('disabled', true);
            $('#' + id + '_save').removeClass('btn-success').addClass('btn-default');
            $('#' + id + '_connect').removeClass('btn-default').addClass('btn-success');
            if (!$('#' + id + '_message').hasClass('text-danger')) {
                $('#' + id + '_message').addClass('text-danger');
                $('#' + id + '_message').removeClass('text-success');
            }
        }
    },
    'fetch_temporary_token': {
        'success': function (id, data) {
            var response_data = data.response_data;
            authPermissionSucceed(id, response_data.fullname, response_data.oauth_key);
        },
        'fail': function (id, message) {
            authPermissionFailed(id, message);
        }
    },
    'remove_auth_data_temporary': {
        'success': function (id, data) {
            authPermissionFailed(id, data.message);
        },
        'fail': function (id, message) {
            authPermissionFailed(id, message);
        }
    },
};

function getParameters(params) {
    var providerClass = params.provider_short_name + '-params';
    var allParameters = $('.' + providerClass);
    params.storage_name = $('#storage_name').val();
    $.each(allParameters, function (key, value) {
        if (!value.disabled) {
            params[value.id] = value.value;
        }
    });
}

$('.auth-permission-button').click(function(e) {
    $(this).click(false);
    $(this).addClass('disabled');
    var providerShortName = this.id.replace('_auth_hyperlink', '');
    oauthOpener(this.href, providerShortName);
    e.preventDefault();
});

$('.auth-cancel').click(function(e) {
    var providerShortName = this.id.replace('_cancel', '');
    authPermissionFailed(providerShortName, '');
    var route = 'remove_auth_data_temporary';
    cancel_auth(providerShortName);
});


function get_token(providerShortName, route) {
    var params = {
        'provider_short_name': providerShortName
    };
    ajaxRequest(params, providerShortName, route);
}

function oauthOpener(url,providerShortName){
    var win = window.open(
        url,
        'OAuth');
    var params = {
        'provider_short_name': providerShortName
    };
    var route = 'fetch_temporary_token';
    var timer = setInterval(function() {
        if (win.closed) {
            clearInterval(timer);
            get_token(providerShortName, route);
        }
    }, 1000, [providerShortName, route]);
}

function authPermissionSucceed(providerShortName, authorizedBy, currentToken){
    var providerClass = providerShortName + '-auth-callback';
    var allFeedbackFields = $('.' + providerClass);
    allFeedbackFields.removeClass('hidden');
    $('#' + providerShortName + '_authorized_by').text(authorizedBy);
    $('#' + providerShortName + '_current_token').text(currentToken);
    authSaveButtonState(providerShortName);
}

function authPermissionFailed(providerShortName, message){
    var providerClass = providerShortName + '-auth-callback';
    var allFeedbackFields = $('.' + providerClass);
    allFeedbackFields.addClass('hidden');
    $('#' + providerShortName + '_authorized_by').text('');
    $('#' + providerShortName + '_current_token').text('');
    $('#' + providerShortName + '_auth_hyperlink').attr('disabled', false);
    $('#' + providerShortName + '_auth_hyperlink').removeClass('disabled');
    authSaveButtonState(providerShortName);
}

function authSaveButtonState(providerShortName) {
    var is_folder_valid = $('#' + providerShortName + '_folder').val() !== '';
    var is_token_valid = $('#' + providerShortName + '_current_token').text().length>0;
    $('#' + providerShortName + '_save').attr('disabled', !(is_folder_valid && is_token_valid));
}

function cancel_auth(providerShortName) {
    var params = {
        'provider_short_name': providerShortName
    };
    var route = 'remove_auth_data_temporary';
    ajaxRequest(params, providerShortName, route);
}
