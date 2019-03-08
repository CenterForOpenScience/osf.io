'use strict';

var $ = require('jquery');
var jQuery = $;
var urls = window.timestampaddUrls;
var timestampCommon = require('js/pages/timestamp-common.js');  // website/static/js/pages
timestampCommon.setWebOrAdmin('admin');


$(function () {
    function getCookie (name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
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
        if ($('#btn-verify').attr('disabled') !== undefined || $('#btn-addtimestamp').attr('disabled') !== undefined) {
            return false;
        }
        timestampCommon.verify({
            urlVerify: urls.verify,
            urlVerifyData: urls.verifyData,
            method: 'POST'
        });
    };

    var btnAddtimestamp_onclick = function () {
        if ($('#btn-verify').attr('disabled') !== undefined || $('#btn-addtimestamp').attr('disabled') !== undefined) {
            return false;
        }
        timestampCommon.add({
            url: urls.addTimestampData,
            method: 'POST'
        });
    };

    var updatePaginationElements = function () {
        // Page info
        var currentPage = $('.listjs-pagination .active a').text();
        var numPages = $('.listjs-pagination li a').last().text();
        $('.pagination .current').text('Page ' + currentPage + ' of ' + numPages);

        // Enable/disable buttons
        $('.pagination #first-page').removeClass('disabled');
        $('.pagination #previous-page').removeClass('disabled');
        $('.pagination #last-page').removeClass('disabled');
        $('.pagination #next-page').removeClass('disabled');
        if (!currentPage || currentPage === '1') {
            $('.pagination #first-page').addClass('disabled');
            $('.pagination #previous-page').addClass('disabled');
        }
        if (currentPage === numPages) {
            $('.pagination #last-page').addClass('disabled');
            $('.pagination #next-page').addClass('disabled');
        }
    };

    $('.pagination #first-page').on('click', function () {
        $('.listjs-pagination li').first().click();
        updatePaginationElements();
    });

    $('.pagination #previous-page').on('click', function () {
        $('.pagination-prev').click();
        updatePaginationElements();
    });

    $('.pagination #next-page').on('click', function () {
        $('.pagination-next').click();
        updatePaginationElements();
    });

    $('.pagination #last-page').on('click', function () {
        $('.listjs-pagination li').last().click();
        updatePaginationElements();
    });

    $('.pagination #pageLength-10').on('click', function () {
        $('#pageLength').val(10).change();
        updatePaginationElements();
    });

    $('.pagination #pageLength-25').on('click', function () {
        $('#pageLength').val(25).change();
        updatePaginationElements();
    });

    $('.pagination #pageLength-50').on('click', function () {
        $('#pageLength').val(50).change();
        updatePaginationElements();
    });

    $(document).ready(function () {
        timestampCommon.init();
        $('#btn-verify').on('click', btnVerify_onclick).focus();
        $('#btn-addtimestamp').on('click', btnAddtimestamp_onclick).focus();
        $('#btn-download').on('click', function () {
            timestampCommon.download();
        });
        updatePaginationElements();
    });
});
