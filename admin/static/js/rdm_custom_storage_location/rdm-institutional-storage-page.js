'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var bootbox = require('bootbox');

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

var clipboard = require('js/clipboard');

var no_storage_name_providers = ['osfstorage', 'onedrivebusiness'];
// type1: get from admin/rdm_addons/api_v1/views.py
var preload_accounts_type1 = ['dropboxbusiness'];
// type2: get from admin/rdm_custom_storage_location/views.py
var preload_accounts_type2 = ['nextcloudinstitutions',
                'ociinstitutions',
                's3compatinstitutions']
// delay time to show growl box; in millisecond
var growlBoxDelay = 5000;
var intervalCheckStatus = 5000;
var list_file_info_export_fail = [];
var list_file_info_restore_fail = [];
var file_name_export_fail = '';
var file_name_restore_fail = '';

function preload(provider, callback) {
    if (preload_accounts_type1.indexOf(provider) >= 0) {
        var div = $('#' + provider + '_authorization_div');
        var institutionId = div.data('institution-id');
        getAccount(provider, institutionId);
        if (provider === 'dropboxbusiness') {
            getAccount('dropboxbusiness_manage', institutionId);
        }
        if (callback) {
            callback();
        }
    } else if (preload_accounts_type2.indexOf(provider) >= 0) {
        // getCredentials(provider, callback);
 	getCredentials(provider, null);
        if (callback) {
            callback();
        }
    } else {
        if (callback) {
            callback();
        }
    }
}

function disable_storage_name(provider) {
    $('#storage_name').attr('disabled',
			    no_storage_name_providers.indexOf(provider) >= 0);
}

function selectedProvider() {
     return $('input[name=\'options\']:checked').val();
}

$(window).on('load', function () {
    var provider = selectedProvider();
    disable_storage_name(provider);
    preload(provider, null);
});

$('[name=options]').change(function () {
    var provider = this.value;
    disable_storage_name(provider);
    preload(provider, null);
});

$('.modal').on('hidden.bs.modal', function (e) {
    $('body').css('overflow', 'auto');
});

$('#institutional_storage_form').submit(function (e) {
    if ($('#institutional_storage_form')[0].checkValidity()) {
        var provider = selectedProvider()
        preload(provider, null);
        var showModal = function () {
            $('#' + provider + '_modal').modal('show');
            $('body').css('overflow', 'hidden');
            $('.modal').css('overflow', 'auto');
            validateRequiredFields(provider);
        };
        if (provider === 'osfstorage' && $('[checked]').val() === 'osfstorage') {
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

$('#s3compatinstitutions_modal input').keyup(function () {
    validateRequiredFields('s3compatinstitutions');
});

$('#s3compatinstitutions_modal input').on('paste', function(e) {
    validateRequiredFields('s3compatinstitutions');
});

$('#ociinstitutions_modal input').keyup(function () {
    validateRequiredFields('ociinstitutions');
});

$('#ociinstitutions_modal input').on('paste', function(e) {
    validateRequiredFields('ociinstitutions');
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

$('#onedrivebusiness_modal input').keyup(function () {
    authSaveButtonState('onedrivebusiness');
});

$('#onedrivebusiness_modal input').on('paste', function(e) {
    authSaveButtonState('onedrivebusiness');
});

function strip_last_slash(s) {
    return s.replace(/\/+$/g, '');
}

function nextcloudinstitutions_host() {
    // url.rstrip('/') in admin/rdm_custom_storage_location/utils.py
    return 'https://' + strip_last_slash($('#nextcloudinstitutions_host').val());
}

function update_nextcloudinstitutions_notification_connid() {
    var connid = nextcloudinstitutions_host() + ':' + $('#nextcloudinstitutions_username').val();
    $('#nextcloudinstitutions_notification_connid').attr('value', connid);
    clipboard('#copy_button_connid');
}

function update_nextcloudinstitutions_notification_url() {
    var osf_domain = strip_last_slash($('#osf_domain').val());
    var url = osf_domain + '/api/v1/addons/nextcloudinstitutions/webhook/';
    $('#nextcloudinstitutions_notification_url').attr('value', url);
    clipboard('#copy_button_url');
}

$('#nextcloudinstitutions_host').on('keyup paste', function () {
    update_nextcloudinstitutions_notification_connid();
    update_nextcloudinstitutions_notification_url();
});
$('#nextcloudinstitutions_username').on('keyup paste', function () {
    update_nextcloudinstitutions_notification_connid();
});

$('#csv_file').on('change', function() {
    var filename = '';
    var fileLists = $(this).prop('files');
    if (fileLists.length > 0) {
        filename = $(this).prop('files')[0].name;
    }
    $('#csv_file_name').text(filename);
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

function disableButtons(providerShortName) {
    $('#' + providerShortName + '_connect').attr('disabled', true);
    $('#' + providerShortName + '_save').attr('disabled', true);
}

function have_csv_ng() {
    var csv_ng = $('#csv_ng');
    return csv_ng.length && csv_ng.text().length && csv_ng.text() !== 'NG=0';
}

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
    if (have_csv_ng()) {
        disableButtons(providerShortName);
	return;
    }

    var params = {
        'provider_short_name': providerShortName
    };
    getParameters(params);
    ajaxRequest(params, providerShortName, route, null);
}

var csrftoken = $('[name=csrfmiddlewaretoken]').val()

function csrfSafeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    crossDomain: false,
    beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
        }
    }
});

function ajaxCommon(type, params, providerShortName, route, callback) {
    if (type === 'POST') {
        params = JSON.stringify(params);
    }
    var url = '../' + route + '/'
    $.ajax({
        url: url,
        type: type,
        data: params,
        contentType: 'application/json; charset=utf-8',
        custom: providerShortName,
        timeout: 120000,
        success: function (data) {
            afterRequest[route].success(this.custom, data);
            if (callback) {
                callback();
            }
        },
        error: function (jqXHR) {
            if (jqXHR.responseJSON != null && ('message' in jqXHR.responseJSON)) {
                afterRequest[route].fail(this.custom, jqXHR.responseJSON.message);
            } else {
                afterRequest[route].fail(this.custom, _('Some errors occurred'));
            }
            if (callback) {
                callback();
            }
        }
    });
}

function ajaxGET(params, providerShortName, route, callback) {
    ajaxCommon('GET', params, providerShortName, route, callback);
}

// ajaxPOST
function ajaxRequest(params, providerShortName, route, callback) {
    ajaxCommon('POST', params, providerShortName, route, callback);
}

var afterRequest = {
    'test_connection': {
        'success': function (id, data) {
            $('#' + id + '_save').attr('disabled', false);
            $('#' + id + '_save').removeClass('btn-default').addClass('btn-success');
            $('#' + id + '_connect').removeClass('btn-success').addClass('btn-default');
            $('#' + id + '_message').html(_(data.message));
            if (!$('#' + id + '_message').hasClass('text-success')) {
                $('#' + id + '_message').addClass('text-success');
                $('#' + id + '_message').removeClass('text-danger');
            }
        },
        'fail': function (id, message) {
            $('#' + id + '_message').html(_(message));
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
            $osf.growl('Success', _('Institutional Storage set successfully'), 'success', growlBoxDelay);
            setTimeout(function() {
                location.reload(true);
            }, growlBoxDelay);
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
    'usermap': {
        'success': function (id, data) {
            usermapDownload(id, data);
        },
        'fail': function (id, message) {
            usermapDownloadFailed(id, message);
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
        title: _('Disconnect Account?'),
        message: '<p class="overflow">' +
            sprintf(_('Are you sure you want to disconnect the %1$s account <strong>%2$s</strong>?<br>'), $osf.htmlEscape(properName), $osf.htmlEscape(accountName)) +
            sprintf(_('This will revoke access to %1$s for all projects using this account.<br><br>'), $osf.htmlEscape(properName)) +
            sprintf(_("Type the following to continue: <strong>%1$s</strong><br><br>"), $osf.htmlEscape(deletionKey)) +
            "<input id='" + $osf.htmlEscape(id) + "' type='text' class='bootbox-input bootbox-input-text form-control'>" +
            '</p>',
        callback: function(confirm) {
            if (confirm) {
                if ($('#'+id).val() == deletionKey) {
                    disconnectAccount(providerShortName, institutionId);
                } else {
                    $osf.growl('Verification failed', 'Strings did not match');
                }
            } else {
                $(elm).removeClass('disabled');
            }
        },
        buttons:{
            confirm:{
                label:_('Disconnect'),
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
    // ajaxRequest(params, providerShortName, route, callback);
    ajaxGET(params, providerShortName, route, callback);
}

function setParameters(provider_short_name, data) {
    var providerClass = provider_short_name + '-params';
    $('.' + providerClass).each(function(i, e) {
        var val = data[$(e).attr('id')];
	if (val) {
            $(e).val(val);
        }
    });

    if (provider_short_name === 'nextcloudinstitutions') {
	update_nextcloudinstitutions_notification_connid();
	update_nextcloudinstitutions_notification_url();
    }
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
            link.off();
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
            link.off();
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
        request2.then(function () {
            getAccount(providerShortName, institutionId);
        });
    });
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
    $('#' + providerShortName + '_current_token').text('********');
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

function reflect_csv_results(data, providerShortName) {
    $('#csv_ok').html('OK=' + data.OK);
    $('#csv_ng').html('NG=' + data.NG);
    $('#csv_report').html(data.report.join('<br/>'));
    $('#csv_usermap').html(JSON.stringify(data.user_to_extuser));

    if (have_csv_ng()) {
        disableButtons(providerShortName);
    } else {
        validateRequiredFields(providerShortName);
    }
}

$('#csv_file').change(function () {
    var provider = selectedProvider();
    var file = $(this).prop('files')[0];

    var fd = new FormData();
    fd.append('provider', provider);
    if (file === undefined) {  // unselected
        fd.append('clear', true);
    } else {
        fd.append($(this).attr('name'), file);
        var providerClass = provider + '-params';
        $('.' + providerClass).each(function(i, e) {
             fd.append($(e).attr('id'), $(e).val());
        });
        fd.append('check_extuser', $('#csv_check_extuser').is(':checked'));
    }
    $.ajax({
        url: '../usermap/',
        type: 'POST',
        data: fd,
        processData: false,
        contentType: false,
        timeout: 30000
    }).done(function (data) {
	reflect_csv_results(data, provider);
    }).fail(function (jqXHR) {
        if (jqXHR.responseJSON != null) {
            reflect_csv_results(jqXHR.responseJSON, provider);
        } else {
            $('#csv_ok').html('');
            $('#csv_ng').html(_('Some errors occurred'));
            $('#csv_report').html('');
            $('#csv_usermap').html('');
        }
    });
});

$('.download-csv').click(function () {
    var provider = selectedProvider()
    var params = {
        'provider': provider
    };
    $('#csv_download_ng').html('');
    ajaxGET(params, provider, 'usermap', null)
});

function saveFile(filename, type, content) {
    if (window.navigator.msSaveOrOpenBlob) {
        var blob = new Blob([content], {type: type});
        window.navigator.msSaveOrOpenBlob(blob, filename);
    }
    else {
        var element = document.createElement('a');
        element.setAttribute('href', 'data:' + type + ',' + encodeURIComponent(content));
        element.setAttribute('download', filename);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }
}

function usermapDownload(id, data) {
    var name = 'usermap-' + selectedProvider() +'.csv';
    saveFile(name, 'text/csv; charset=utf-8', data);
}

function usermapDownloadFailed(id, message) {
    $('#csv_download_ng').html(message);
}


// Start - Storage location - Actions

afterRequest.delete = {
    'success': function (id) {
        $('#location_' + id).remove();
    },
    'fail': function (id) {
        var message = sprintf(_('Unable to delete location %1$s'), id)
        $osf.growl('Error', message, 'success', growlBoxDelay);
    }
}

$('.delete-location').click(function () {
    var id = this.dataset.id;
    // var providerShortName = this.dataset.provide;

    deleteLocation(id);
});

function deleteLocation(id) {
    var route = 'delete';
    var url = id + '/' + route + '/';
    $.ajax({
        url: url,
        type: 'DELETE',
        data: {},
        contentType: 'application/json; charset=utf-8',
        custom: id,
        timeout: 120000,
        success: function (data) {
            afterRequest[route].success(this.custom, data);
            var new_url = document.location.href;
            var window_page = window.page;
            var value = window_page.pageCount % window_page.perPage;
            if(value - 1 === 0){
              if(window_page.pageNumber <= 1){
                window.history.pushState({}, '', new_url.split('?')[0]);
              }
              else if(window_page.pageNumber < window_page.pageNumPages){
                window.location.reload();
              }
              else{
                new_url= new URL(document.location.href);
                new_url.searchParams.set('page', window_page.pageNumber - 1);
                window.location.href = new_url.toString();
              }
            }
            else{
                window.location.reload();
            }
        },
        error: function (jqXHR) {
            if (jqXHR.responseJSON != null && ('message' in jqXHR.responseJSON)) {
                afterRequest[route].fail(this.custom, jqXHR.responseJSON.message);
            } else {
                afterRequest[route].fail(this.custom, _('Some errors occurred'));
            }
        }
    });
}


// Start - institutional storages screen - Actions

function showViewExportDataButton(element, location_id) {
    var $viewExportDataButton = $(element);
    if ($viewExportDataButton.hasClass('hidden')) {
        $viewExportDataButton.removeClass('hidden');
    }
    $viewExportDataButton.data('location', location_id);
}

function hiddenViewExportDataButton(element) {
    var $viewExportDataButton = $(element);
    if (!$viewExportDataButton.hasClass('hidden')) {
        $viewExportDataButton.addClass('hidden');
    }
    $viewExportDataButton.removeData('location');
}

$('.row-storage select.location-select').change(function (event) {
    event.preventDefault();
    var institution_id = window.contextVars.institution_id;
    var source_id = this.dataset.storage;
    var location_id = $(this).val();
    var $parent = $(this).parents('.row-storage');
    var $viewExportDataButton = $parent.find('button.view-export-data');
    var params = {
        'institution_id': institution_id,
        'source_id': source_id,
        'location_id': location_id,
    };
    var route = 'check-data';
    var url = '/custom_storage_location/export_data/' + route + '/';
    $.ajax({
        url: url,
        type: 'POST',
        data: JSON.stringify(params),
        contentType: 'application/json; charset=utf-8',
        custom: {'element': $viewExportDataButton, 'location_id': location_id},
        timeout: 120000,
        success: function (data) {
            if (data.has_data === true) {
                showViewExportDataButton(this.custom.element, this.custom.location_id);
            } else {
                hiddenViewExportDataButton(this.custom.element);
            }
        },
        error: function () {
            hiddenViewExportDataButton(this.custom.element);
        }
    });
});

$('.row-storage button.view-export-data').click(function (event) {
    event.preventDefault();
    var params = {'storage_id': $(this).data('storage'), 'location_id': $(this).data('location')}
    var url = window.contextVars.export_data_list_url + '?' + $.param(params);
    window.location.replace(url);
});


// Start - Export data - Actions

function exportState(element) {
    var $parent = $(element).parent();
    var $exportButton = $parent.find('.export-button');
    $exportButton.prop('disabled', false);
    $exportButton.removeClass('disabled');

    var $stopExportButton = $parent.find('.stop-export-button');
    $stopExportButton.prop('disabled', true);
    $stopExportButton.addClass('disabled');
}

function stopExportState(element) {
    var $parent = $(element).parent();
    var $exportButton = $parent.find('.export-button');
    $exportButton.prop('disabled', true);
    $exportButton.addClass('disabled');

    var $stopExportButton = $parent.find('.stop-export-button');
    $stopExportButton.prop('disabled', false);
    $stopExportButton.removeClass('disabled');
}

$('.export-button').click(function (event) {
    event.preventDefault();
    $(this).prop('disabled', true);
    $(this).addClass('disabled');
    var institution_id = window.contextVars.institution_id;
    var source_id = this.dataset.storage | $('#source-select').val();
    var location_id = $('#location-select-' + source_id).val() | $('#location-select').val();

    exportData(institution_id, source_id, location_id, this);
});

function exportData(institution_id, source_id, location_id, element) {
    var params = {
        'institution_id': institution_id,
        'source_id': source_id,
        'location_id': location_id,
    };
    var route = 'export';
    var url = '/custom_storage_location/export_data/' + route + '/';
    var task_id;
    var key = source_id + '_' + location_id;
    window.contextVars[key] = {};
    $.ajax({
        url: url,
        type: 'POST',
        data: JSON.stringify(params),
        contentType: 'application/json; charset=utf-8',
        custom: {'element': element, 'key': key},
        timeout: 120000,
        success: function (data) {
            var message;
            var messageType = 'success';
            var need_reload = 0;
            task_id = data.task_id;

            if (data.task_state === 'SUCCESS') {
                // task_state in (SUCCESS, )
                exportState(this.custom.element);
                message =  _('Export data successfully.');
                need_reload = 1;

                var $parent = $(this.custom.element).parents('.row-storage');
                if ($parent.length) {
                    var $viewExportDataButton = $parent.find('button.view-export-data');
                    showViewExportDataButton($viewExportDataButton, location_id)
                }
            } else if (data.task_state === 'FAILURE') {
                // task_state in (FAILURE, )
                exportState(this.custom.element);
                message = _('Error occurred while exporting data.');
                messageType = 'danger';
            } else {
                // task_state in (PENDING, STARTED, )
                stopExportState(this.custom.element);
                message = _('Export data in background.');
                window.contextVars[this.custom.key].exportInBackground = true;

                var $exportButton = $(this.custom.element);
                var $stopExportButton = $exportButton.parent().find('.stop-export-button');
                $stopExportButton.data('task_id', task_id);
            }
            $osf.growl(_('Export Data'), message, messageType, growlBoxDelay);
            if (!!need_reload) {
                setTimeout(function() {
                     window.location.reload();
                }, growlBoxDelay);
            }

            if (window.contextVars[this.custom.key].exportInBackground) {
                // var x = 0;
                window.contextVars[this.custom.key].intervalID = window.setInterval(function () {
                    checkStatusExportData(institution_id, source_id, location_id, task_id, element);
                    // ++x === 5 && window.clearInterval(window.contextVars[this.custom.key].intervalID);
                }, intervalCheckStatus);
            }
        },
        error: function (jqXHR) {
            exportState(this.custom.element);
            var message = _('Cannot export data.');
            if (jqXHR.responseJSON != null && ('message' in jqXHR.responseJSON)) {
                message = _(jqXHR.responseJSON.message);
            }
            $osf.growl(_('Export Data'), message, 'danger', growlBoxDelay);
        }
    });
}

$('.stop-export-button').click(function (event) {
    event.preventDefault();
    $(this).prop('disabled', true);
    $(this).addClass('disabled');
    var institution_id = window.contextVars.institution_id;
    var source_id = this.dataset.storage | $('#source-select').val();
    var location_id = $('#location-select-' + source_id).val() | $('#location-select').val();
    var task_id = $(this).data('task_id');

    stopExportData(institution_id, source_id, location_id, task_id, this);
});

function stopExportData(institution_id, source_id, location_id, task_id, element) {
    var key = source_id + '_' + location_id;
    var params = {
        'institution_id': institution_id,
        'source_id': source_id,
        'location_id': location_id,
        'task_id': task_id,
    };
    var route = 'stop-export';
    var url = '/custom_storage_location/export_data/' + route + '/';
    $.ajax({
        url: url,
        type: 'POST',
        data: JSON.stringify(params),
        contentType: 'application/json; charset=utf-8',
        custom: {'element': element, 'key': key},
        timeout: 120000,
        success: function (data) {
            window.contextVars[this.custom.key].exportInBackground && window.clearInterval(window.contextVars[this.custom.key].intervalID);
            window.contextVars[this.custom.key].intervalID = undefined;
            window.contextVars[this.custom.key].exportInBackground = false;
            var message;
            var messageType = 'success';
            task_id = data.task_id;

            if (data.task_state === 'SUCCESS') {
                // task_state in (SUCCESS, )
                // old task_state in (ABORTED, )
                exportState(this.custom.element);
                message = _('Stop exporting successfully.');
            } else if (data.task_state === 'FAILURE') {
                // task_state in (FAILURE, )
                stopExportState(this.custom.element);
                message = _('Error occurred while stopping export data.');
                messageType = 'danger';
            } else {
                // task_state in (PENDING, STARTED, )
                message = _('Stop exporting in background.');
                window.contextVars[this.custom.key].stopExportInBackground = true;
            }
            $osf.growl(_('Stop Export Data'), message, messageType, growlBoxDelay);

            if (window.contextVars[this.custom.key].stopExportInBackground) {
                // var x = 0;
                window.contextVars[this.custom.key].intervalID = window.setInterval(function () {
                    checkStatusExportData(institution_id, source_id, location_id, task_id, element);
                    // ++x === 5 && window.clearInterval(window.contextVars[this.custom.key].intervalID);
                }, intervalCheckStatus);
            }
        },
        error: function (jqXHR) {
            stopExportState(this.custom.element);
            var title = _('Stop Export Data');
            var message = _('Cannot stop exporting data.');
            var messageType = 'danger';
            var need_reload = 0;
            if (jqXHR.responseJSON != null && ('message' in jqXHR.responseJSON)) {
                var data = jqXHR.responseJSON;
                message = _(data.message);
                if ('task_state' in data && 'status' in data) {
                    if (data.task_state === 'SUCCESS') {
                        // task_state in (SUCCESS)
                        exportState(this.custom.element);
                    }

                    if (data.status === 'Completed') {
                        var $parent = $(this.custom.element).parents('.row-storage');
                        if ($parent.length) {
                            var $viewExportDataButton = $parent.find('button.view-export-data');
                            showViewExportDataButton($viewExportDataButton, location_id)
                        }
                        title = _('Export Data');
                        message = _('Export data successfully.');
                        messageType = 'success';
                        need_reload = 1;
                    } else if (data.status === 'Error') {
                        title = _('Export Data');
                        message = _('Export data failed.');
                    }
                }
            }
            $osf.growl(title, message, messageType, growlBoxDelay);
            if (!!need_reload) {
                setTimeout(function() {
                     window.location.reload();
                }, growlBoxDelay);
            }
        }
    });
}

function checkStatusExportData(institution_id, source_id, location_id, task_id, element) {
    var params = {
        'institution_id': institution_id,
        'source_id': source_id,
        'location_id': location_id,
        'task_id': task_id,
    };
    var route = 'check-export';
    var url = '/custom_storage_location/export_data/' + route + '/';
    var key = source_id + '_' + location_id;
    $.ajax({
        url: url,
        type: 'POST',
        data: JSON.stringify(params),
        contentType: 'application/json; charset=utf-8',
        custom: {'element': element, 'key': key},
        timeout: 120000,
        success: function (data) {
            var title = window.contextVars[this.custom.key].stopExportInBackground ? _('Stop Export Data') : _('Export Data');
            var message;
            var messageType = 'success';
            var need_reload = 0;

            if (data.task_state === 'SUCCESS') {
                // task_state in (SUCCESS, )
                window.clearInterval(window.contextVars[this.custom.key].intervalID);
                window.contextVars[this.custom.key].intervalID = undefined;

                exportState(this.custom.element);
                message = _('Export data successfully.');
                if (window.contextVars[this.custom.key].stopExportInBackground) {
                    message = _('Stop exporting successfully.');
                }

                if (data.status === 'Completed') {
                    var $parent = $(this.custom.element).parents('.row-storage');
                    if ($parent.length) {
                        var $viewExportDataButton = $parent.find('button.view-export-data');
                        showViewExportDataButton($viewExportDataButton, location_id)
                    }
                    need_reload = 1;
                    if (data.result.list_file_info_export_not_found.length > 0) {
                        var data_res = data.result.list_file_info_export_not_found;
                        var text_show_file = '';
                        file_name_export_fail = data.result.file_name_export_fail;
                        need_reload = 0;
                        $('#showFileExportNotExistModal').modal('show');
                        list_file_info_export_fail = [['File path', 'File name', 'Provider', 'Size']];
                        data_res.forEach(function (file) {
                            list_file_info_export_fail.push([file.path, file.name, file.provider, file.size]);
                            text_show_file += "<tr><td>" + file.path + "</td><td>" + file.name + "</td><td>"
                                                + file.provider + "</td><td>" + file.size + " Bytes</td>";
                        });
                        $('.table-ng-file-export-not-exist').html(text_show_file);
                        $('.table-ng-file-export-not-exist').css('word-break', 'break-word');
                    }
                } else if (!window.contextVars[this.custom.key].stopExportInBackground) {
                    messageType = 'danger';
                    message = _('Export data failed.');
                }
            } else if (data.task_state === 'FAILURE') {
                // task_state in (FAILURE, )
                window.clearInterval(window.contextVars[this.custom.key].intervalID);
                window.contextVars[this.custom.key].intervalID = undefined;

                messageType = 'danger';
                if (window.contextVars[this.custom.key].stopExportInBackground) {
                    stopExportState(this.custom.element);
                    message = _('Error occurred while stopping export data.');
                } else {
                    exportState(this.custom.element);
                    message = _('Error occurred while exporting data.');
                }
            }
            if (!window.contextVars[this.custom.key].intervalID) {
                $osf.growl(title, message, messageType, growlBoxDelay);
                window.contextVars[this.custom.key].intervalID = undefined;
                window.contextVars[this.custom.key].exportInBackground = false;
                window.contextVars[this.custom.key].stopExportInBackground = false;
            }
            if (!!need_reload) {
                setTimeout(function() {
                     window.location.reload();
                }, growlBoxDelay);
            }
        },
        error: function (jqXHR) {
            // keep for debug
        }
    });
}


// Start - Delete Export data - Actions

$('#checkDelete').on('click', function() {
    var list_export_delete_id = $("#checkDelete").val() + '#';
    $('#bodydeletemodal').append(
        "<input type='text' value='" + list_export_delete_id +
        "' id='input_export_data' class='buckinput' name='list_id_export_data' style='display: none;' />");
});

$('#delete_permanently_button').on('click', function() {
    var list_export_data = $('input[type=checkbox][name=check_revert_export]');
    var list_export_id = '';
    for (var i = 0; i < list_export_data.length; i++) {
        if (list_export_data[i].checked) {
            list_export_id += list_export_data[i].id + '#';
        }
    }
    $('#bodyDeleteExport').append("<input type='hidden' value='"+ list_export_id +"' id='input_export_data' class='buckinput' name='list_id_export_data' />");
    $osf.confirmDangerousAction({
        title: _('Are you sure you want to permanently delete these export data?'),
        callback: function() {
            $('#deleteExportForm').submit();
        },
        buttons: {
            success: {
                label: _('Delete Permanently')
            }
        }
    });
});


// Start - Revert Export data - Actions

$('#revert_button').on('click', function () {
    var list_export_revert_id = $("#revert_button").val() + '#';
    $('#bodyrevertmodal').append(
        "<input type='text' value='" + list_export_revert_id +
        "' id='input_export_data' class='buckinput' name='list_id_export_data' style='display: none;' />");
});

$('.cancel_modal').on('click', function () {
    $('#input_export_data').remove();
});


// Start - Check Export data - Actions

$('#checkExportData').on('click', function () {
    var url = './check_export_data/';
    $('#checkExportData').prop('disabled', true);
    $.ajax({
        url: url,
        type: 'GET',
        contentType: 'application/json; charset=utf-8',
    }).done(function (response) {
        var data_res = response;
        $('#checkExportDataModal').modal('show');
        var text_check_export = "<p>OK: " + data_res.ok + "/" + data_res.total + " files<br/>" +
            "NG: " + data_res.ng + "/" + data_res.total + " files</p>";
        var text_current = '';
        data_res.list_file_ng.forEach(function (file) {
            text_current += "<tr><td>" + file.path + "</td><td>" + file.size + " Bytes</td>" +
                "<td>" + file.version_id + "</td><td>" + file.reason + "</td></tr>";
        });
        $('.text-check-export-data').html(text_check_export);
        $('.table-ng').html(text_current);
        $('.table-ng').css('word-break', 'break-word');
    }).fail(function (jqXHR) {
        $('#checkExportData').prop('disabled', false);
        var message = _(jqXHR.responseJSON.message);
        $osf.growl('Error', message, 'error', growlBoxDelay);
    });
});

$('#cancelExportDataModal').on('click', function () {
    $('#checkExportData').prop('disabled', false);
});

$('#checkExportDataModal').on('hidden.bs.modal', function () {
  $('#checkExportData').prop('disabled', false);
});


// Start - Restore Export data - Actions

function disableRestoreButton() {
    // Disable 'Restore' button
    var $restore_button = $('#restore_button');
    $restore_button.addClass('disabled');
    $restore_button.attr('disabled', true);
}

function enableRestoreFunction() {
    // Enable 'Restore' button, disable 'Stop restoring' button
    var $restore_button = $('#restore_button');
    $restore_button.removeClass('disabled');
    $restore_button.attr('disabled', false);

    var $stop_restore_button = $('#stop_restore_button');
    $stop_restore_button.addClass('disabled');
    $stop_restore_button.attr('disabled', true);
}

function enableStopRestoreFunction() {
    // Enable 'Stop restoring' button, disable 'Restore' button
    var $restore_button = $('#restore_button');
    $restore_button.addClass('disabled');
    $restore_button.attr('disabled', true);

    var $stop_restore_button = $('#stop_restore_button');
    $stop_restore_button.removeClass('disabled');
    $stop_restore_button.attr('disabled', false);
}

function enableCheckRestoreFunction() {
    // Enable 'Check export data' button, disable 'Stop restoring' button
    var $check_restore_button = $('#check_restore_button');
    $check_restore_button.removeClass('disabled');
    $check_restore_button.attr('disabled', false);

    var $stop_restore_button = $('#stop_restore_button');
    $stop_restore_button.addClass('disabled');
    $stop_restore_button.attr('disabled', true);
}

$('#cancel_restore_modal_button').on('click', function () {
    enableRestoreFunction();
});

$('#restore').on('hidden.bs.modal', function () {
    enableRestoreFunction();
});

$('#restore_button').on('click', function () {
    var data = {};
    data['destination_id'] = $('#destination_storage').val();
    disableRestoreButton();
    $.ajax({
        url: 'restore_export_data/',
        type: 'post',
        data: data
    }).done(function (response) {
        if (response['message']) {
            enableRestoreFunction();
            // Show error message
            $osf.growl(_('Restore Export Data'), result['message'], 'danger', growlBoxDelay);
        } else if (response['task_id']) {
            enableStopRestoreFunction();
            restore_task_id = response['task_id'];
            setTimeout(function () {
                checkTaskStatus(restore_task_id, 'Restore');
            }, intervalCheckStatus);
        } else {
            $('#restore').modal('show');
        }
    }).fail(function (jqXHR) {
        enableRestoreFunction();
        var data = jqXHR.responseJSON;
        if (data && data['message']) {
            $osf.growl(_('Restore Export Data'), _(data['message']), 'danger', growlBoxDelay);
        }
    });
});

$('#stop_restore_button').on('click', function () {
    var $stop_restore_button = $('#stop_restore_button');
    $stop_restore_button.addClass('disabled');
    $stop_restore_button.attr('disabled', true);
    var data = {
        task_id: restore_task_id,
        destination_id: $('#destination_storage').val(),
    };
    $.ajax({
        url: 'stop_restore_export_data/',
        type: 'post',
        data: data
    }).done(function (response) {
        stop_restore_task_id = response['task_id'];
        setTimeout(function () {
            checkTaskStatus(stop_restore_task_id, 'Stop Restore');
        }, intervalCheckStatus);
    }).fail(function (jqXHR) {
        enableStopRestoreFunction();
        var data = jqXHR.responseJSON;
        if (data && data['message']) {
            $osf.growl(_('Stop Export Data'), _(data['message']), 'danger', growlBoxDelay);
        }
    });
});

function checkTaskStatus(task_id, task_type) {
    var data = {task_id: task_id, task_type: task_type};
    $.ajax({
        url: 'task_status/',
        type: 'get',
        data: data
    }).done(function (response) {
        var state = response['state'];
        var result = response['result'];
        var result_task_id = response['task_id'];
        var result_task_type = response['task_type'];
        if (state === 'SUCCESS') {
            if (result_task_type === 'Restore') {
                // Done restoring export data
                enableCheckRestoreFunction();
                $osf.growl(_('Restore Export Data'), _('Restore completed.'), 'success', growlBoxDelay);
                if (result.list_file_restore_fail.length > 0) {
                    var data_res = result.list_file_restore_fail;
                    var text_show_file = '';
                    $('#showFileRestoreNotExistModal').modal('show');
                    file_name_restore_fail = result.file_name_restore_fail;
                    list_file_info_restore_fail = [['File path', 'File name', 'Provider', 'Size']];
                    data_res.forEach(function (file) {
                        list_file_info_restore_fail.push([file.path, file.name, file.provider, file.size]);
                        text_show_file += "<tr><td>" + file.path + "</td><td>" + file.name + "</td><td>"
                                            + file.provider + "</td><td>" + file.size + " Bytes</td>";
                    });
                    $('.table-ng-file-restore-not-exist').html(text_show_file);
                    $('.table-ng-file-restore-not-exist').css('word-break', 'break-word');
                }
            } else if (result_task_type === 'Stop Restore') {
                // Done stopping restore export data
                enableRestoreFunction();
                $osf.growl(_('Stop Restore Export Data'), _('Stopped restoring data process.'), 'success', growlBoxDelay);
            }
        } else if (state === 'PENDING' || state === 'STARTED') {
            // Redo check task status after 2 seconds
            setTimeout(function () {
                checkTaskStatus(task_id, task_type);
            }, intervalCheckStatus);
        } else {
            if (state !== 'ABORTED') {
                enableRestoreFunction();
            }
            if (result && result['message']) {
                var title = '';
                if (result_task_type === 'Restore'){
                    title = _('Restore Export Data');
                } else if (result_task_type === 'Stop Restore') {
                    title = _('Stop Restore Export Data');
                }
                $osf.growl(title, _(result['message']), 'danger', growlBoxDelay);
            }
        }
    }).fail(function (jqXHR) {
        enableRestoreFunction();
        var data = jqXHR.responseJSON;
        if (data && data['result']) {
            var title = '';
            if (task_type === 'Restore'){
                title = _('Restore Export Data');
            } else if (task_type === 'Stop Restore') {
                title = _('Stop Restore Export Data');
            }
            $osf.growl(title, _(data['result']), 'danger', growlBoxDelay);
        }
    });
}

// Catch event when click Restore button in modal on the DataInformation screen
$('#start_restore_modal_button').on('click', function () {
    var data = {};
    data['destination_id'] = $('#destination_storage').val();
    data['is_from_confirm_dialog'] = true;
    // Call enableStopRestoreFunction() when click Restore button
    $.ajax({
        url: 'restore_export_data/',
        type: 'post',
        data: data
    }).done(function (response) {
        // Get task_id when call ajax successful
        restore_task_id = response['task_id'];
        if (!restore_task_id) {
            return;
        }
        enableStopRestoreFunction();
        setTimeout(function () {
            checkTaskStatus(restore_task_id, 'Restore');
        }, intervalCheckStatus);
    }).fail(function (jqXHR) {
        // Call enableRestoreFunction() when fail
        enableRestoreFunction();
        var data = jqXHR.responseJSON;
        if (data && data['message']) {
            $osf.growl(_('Restore Export Data'), _(data['message']), 'danger', growlBoxDelay);
        }
    });
});


// Start - Check Restore exported data - Actions

$('#check_restore_button').on('click', function () {
    var destination_id = $('select#destination_storage').val();
    var url = 'check_restore_data/?destination_id=' + destination_id;
    $(this).prop('disabled', true);
    $.ajax({
        url: url,
        type: 'GET',
        contentType: 'application/json; charset=utf-8',
    }).done(function (response) {
        var data_res = response;
        $('#checkRestoreDataModal').modal('show');
        var text_check_export = "<p>OK: " + data_res.ok + "/" + data_res.total + " files<br/>" +
            "NG: " + data_res.ng + "/" + data_res.total + " files</p>";
        var text_current = '';
        data_res.list_file_ng.forEach(function (file) {
            text_current += "<tr><td>" + file.path + "</td><td>" + file.size + " Bytes</td>" +
                "<td>" + file.version_id + "</td><td>" + file.reason + "</td></tr>";
        });
        $('.text-check-restore-data').html(text_check_export);
        $('.table-ng-restore').html(text_current);
        $('.table-ng-restore').css('word-break', 'break-word');
    }).fail(function (jqXHR) {
        $('#check_restore_button').prop('disabled', false);
        var message = jqXHR.responseJSON.message;
        $osf.growl('Error', _(message), 'error', growlBoxDelay);
    });
});

$('#cancelRestoreDataModal').on('click', function () {
    $('#check_restore_button').prop('disabled', false);
});

$('#checkRestoreDataModal').on('hidden.bs.modal', function () {
  $('#check_restore_button').prop('disabled', false);
});

function exportToCsv(filename, rows) {
    var processRow = function (row) {
        var finalVal = '';
        for (var j = 0; j < row.length; j++) {
            var innerValue = row[j] === null ? '' : row[j].toString();
            if (row[j] instanceof Date) {
                innerValue = row[j].toLocaleString();
            };
            var result = innerValue.replace(/"/g, '""');
            if (result.search(/("|,|\n)/g) >= 0)
                result = '"' + result + '"';
            if (j > 0)
                finalVal += ',';
            finalVal += result;
        }
        return finalVal + '\n';
    };

    var csvFile = '';
    for (var i = 0; i < rows.length; i++) {
        csvFile += processRow(rows[i]);
    }

    var blob = new Blob([csvFile], { type: 'text/csv;charset=utf-8;' });
    if (navigator.msSaveBlob) { // IE 10+
        navigator.msSaveBlob(blob, filename);
    } else {
        var link = document.createElement("a");
        if (link.download !== undefined) { // feature detection
            // Browsers that support HTML5 download attribute
            var url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
}

$('.cancel_modal_show_file_export_not_exist').on('click', function () {
    list_file_info_export_fail = [];
    file_name_export_fail = '';
    setTimeout(function () {
        window.location.reload();
    }, 1000);
});

$('.download_file_export_not_exist').on('click', function () {
    exportToCsv(file_name_export_fail, list_file_info_export_fail);
});

$('.cancel_modal_show_file_restore_not_exist').on('click', function () {
    list_file_info_restore_fail = [];
    file_name_restore_fail = '';
});

$('.download_file_restore_not_exist').on('click', function () {
    exportToCsv(file_name_restore_fail, list_file_info_restore_fail);
});
