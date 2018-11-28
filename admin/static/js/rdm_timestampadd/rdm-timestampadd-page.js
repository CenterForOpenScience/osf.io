'use strict';

var $ = require('jquery');
var jQuery = $;
var Raven = require('raven-js');
var urls = window.timestampaddUrls;
var timestampCommon = require('js/pages/timestamp-common.js');  // website/static/js/pages


$(function () {
    function getCookie (name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    var csrftoken = getCookie('admin-csrf');
    function csrfSafeMethod (method) {
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

    var btnVerify_onclick = function () {
        if ($('#btn-verify').attr('disabled') != undefined || $('#btn-addtimestamp').attr('disabled') != undefined) {
            return false;
        }
        timestampCommon.verify({
            urlVerify: urls.verify,
            urlVerifyData: urls.verifyData,
            method: 'POST'
        });
    };

    var btnAddtimestamp_onclick = function () {
        if ($('#btn-verify').attr('disabled') != undefined || $('#btn-addtimestamp').attr('disabled') != undefined) {
            return false;
        }
        timestampCommon.add({
            url: urls.addTimestampData,
            method: 'POST'
        });
    };

    $('#addTimestampAllCheck').on('change', function () {
        $('input[id=addTimestampCheck]').prop('checked', this.checked);
    });

    var document_onready = function () {
        $('#btn-verify').on('click', btnVerify_onclick).focus();
        $('#btn-addtimestamp').on('click', btnAddtimestamp_onclick).focus();
    };
    $(document).ready(document_onready);
});
