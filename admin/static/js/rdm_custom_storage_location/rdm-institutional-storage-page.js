'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Cookie = require('js-cookie');
var bootbox = require('bootbox');

var _ = require('js/rdmGettext')._;

var no_storage_name_providers = ['osfstorage',
				 'dropboxbusiness',
				 'nextcloudinstitutions'];
// type1: get from admin/rdm_addons/api_v1/views.py
var preload_accounts_type1 = ['dropboxbusiness'];
// type2: get from admin/rdm_custom_storage_location/views.py
var preload_accounts_type2 = ['nextcloudinstitutions']

function preload(provider, callback) {
    if (preload_accounts_type1.indexOf(provider) >= 0) {
        var div = $('#' + provider + '_authorization_div');
        var institutionId = div.data('institution-id');
        getAccount(provider, institutionId);
        if (provider === 'dropboxbusiness') {
            getAccount('dropboxbusiness_manage', institutionId);
        }
	callback();
    } else if (preload_accounts_type2.indexOf(provider) >= 0) {
        getCredentials(provider, callback);
    } else {
	callback();
    }
}

function disable_storage_name(provider) {
    $('#storage_name').attr('disabled',
			    no_storage_name_providers.indexOf(provider) >= 0);
}

$(window).on('load', function () {
     var selectedProvider = $('input[name=\'options\']:checked').val();
     disable_storage_name(selectedProvider);
});

$('[name=options]').change(function () {
    disable_storage_name(this.value);
});

$('.modal').on('hidden.bs.modal', function (e) {
    $('body').css('overflow', 'auto');
});

$('#institutional_storage_form').submit(function (e) {
    if ($('#institutional_storage_form')[0].checkValidity()) {
        var selectedProvider = $('input[name=\'options\']:checked').val();
        preload(selectedProvider, function() {
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
        });
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

$('#nextcloudinstitutions_modal input').keyup(function () {
    validateRequiredFields('nextcloudinstitutions');
});

$('#nextcloudinstitutions_modal input').on('paste', function(e) {
    validateRequiredFields('nextcloudinstitutions');
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
    ajaxRequest(params, providerShortName, route, null);
}

function ajaxRequest(params, providerShortName, route, callback) {
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
            if (callback) {
                callback();
            }
        },
        error: function (jqXHR) {
            if(jqXHR.responseJSON != null && ('message' in jqXHR.responseJSON)){
                afterRequest[route].fail(this.custom, jqXHR.responseJSON.message);
            }else{
                afterRequest[route].fail(this.custom, _('Some errors occurred'));
            }
            if (callback) {
                callback();
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
    'credentials': {
        'success': function (id, data) {
            setParameters(id, data);
        },
        'fail': function (id, message) {
            setParametersFailed(id, message);
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

function authoriseOnClick(elm) {
    var providerShortName = elm.id.replace('_auth_hyperlink', '');
    var institutionId = $(elm).data('institution-id');
    oauthOpener(elm.href, providerShortName, institutionId);
}

$('.auth-permission-button').click(function(e) {
    $(this).click(false);
    $(this).addClass('disabled');
    authoriseOnClick(this);
    e.preventDefault();
});

function disconnectOnClick(elm, properName, accountName) {
    var providerShortName = elm.id.replace('_disconnect_hyperlink', '');
    var institutionId = $(elm).data('institution-id');

    var deletionKey = Math.random().toString(36).slice(-8);
    var id = providerShortName + "DeleteKey";
    bootbox.confirm({
        title: 'Disconnect Account?',
        message: '<p class="overflow">' +
            'Are you sure you want to disconnect the ' + $osf.htmlEscape(properName) + ' account <strong>' +
            $osf.htmlEscape(accountName) + '</strong>?<br>' +
            'This will revoke access to ' + $osf.htmlEscape(properName) + ' for all projects using this account.<br><br>' +
            "Type the following to continue: <strong>" + $osf.htmlEscape(deletionKey) + "</strong><br><br>" +
            "<input id='" + $osf.htmlEscape(id) + "' type='text' class='bootbox-input bootbox-input-text form-control'>" +
            '</p>',
        callback: function(confirm) {
            if (confirm) {
                if ($('#'+id).val() == deletionKey) {
                    disconnectAccount(providerShortName, institutionId);
                } else {
                    $osf.growl('Verification failed', 'Strings did not match');
                }
            }
        },
        buttons:{
            confirm:{
                label:'Disconnect',
                className:'btn-danger'
            }
        }
    });
}

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
    ajaxRequest(params, providerShortName, route, null);
}

function getCredentials(providerShortName, callback) {
    var params = {
        'provider_short_name': providerShortName
    };
    var route = 'credentials';
    ajaxRequest(params, providerShortName, route, callback);
}

function setParameters(provider_short_name, data) {
    var providerClass = provider_short_name + '-params';
    $('.' + providerClass).each(function(i, e) {
        var val = data[$(e).attr('id')];
	if (val) {
            $(e).val(val);
        }
    });
}

function setParametersFailed(provider_short_name, message) {
}

function getAccount(providerShortName, institutionId) {
    // get an External Account for Institutions
    var url = '/addons/api/v1/settings/' + providerShortName + '/' + institutionId + '/accounts/';
    var request = $.get(url);
    request.done(function (data) {
        if (data.accounts.length > 0) {
            authPermissionSucceedWithoutToken(providerShortName, data.accounts[0].display_name);
            $('#' + providerShortName + '_auth_hyperlink').addClass('disabled');
            var link = $('#' + providerShortName + '_disconnect_hyperlink');
            link.click(false);
            link.click(function (e) {
                $(this).click(false);
                $(this).addClass('disabled');
                disconnectOnClick(this, data.accounts[0].provider_name, data.accounts[0].display_name);
                e.preventDefault();
            });
            link.removeClass('disabled');
            $('.' + providerShortName + '-disconnect-callback').removeClass('hidden');
        } else {
            var link = $('#' + providerShortName + '_auth_hyperlink');
            link.click(function (e) {
                $(this).click(false);
                $(this).addClass('disabled');
                authoriseOnClick(this);
                e.preventDefault();
            });
            link.removeClass('disabled');
            $('#' + providerShortName + '_authorization_div').addClass('hidden');
            $('.' + providerShortName + '-disconnect-callback').addClass('hidden');
        }
    }).fail(function (data) {
        if ('message' in data) {
            authPermissionFailedWithoutToken(providerShortName, data.message);
        } else {
            authPermissionFailedWithoutToken(providerShortName, _('Some errors occurred'));
        }
    });
}

function disconnectAccount(providerShortName, institutionId) {
    var url = '/addons/api/v1/settings/' + providerShortName + '/' + institutionId + '/accounts/';
    var request = $.get(url);
    request.then(function (data) {
        url = '/addons/api/v1/oauth/accounts/' + data.accounts[0].id + '/' + institutionId + '/';
        var request2 = $.ajax({
            url: url,
            type: 'DELETE'
        });
    }).then(
        function () {
            getAccount(providerShortName, institutionId);
        }
    );
}

function oauthOpener(url,providerShortName,institutionId){
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
            if (providerShortName === 'dropboxbusiness' ||
                providerShortName === 'dropboxbusiness_manage') {
                getAccount(providerShortName, institutionId);
            } else {
                get_token(providerShortName, route);
            }
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

function authPermissionSucceedWithoutToken(providerShortName, authorizedBy){
    var providerClass = providerShortName + '-auth-callback';
    var allFeedbackFields = $('.' + providerClass);
    allFeedbackFields.removeClass('hidden');
    $('#' + providerShortName + '_authorized_by').text(authorizedBy);
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

function authPermissionFailedWithoutToken(providerShortName, message){
    var providerClass = providerShortName + '-auth-callback';
    var allFeedbackFields = $('.' + providerClass);
    allFeedbackFields.addClass('hidden');
    $('#' + providerShortName + '_authorized_by').text('');
    $('#' + providerShortName + '_auth_hyperlink').attr('disabled', false);
    $('#' + providerShortName + '_auth_hyperlink').removeClass('disabled');
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
    ajaxRequest(params, providerShortName, route, null);
}
