'use strict';

var $ = require('jquery');
var Cookie = require('js-cookie');
var urls = window.timestampaddUrls;
var timestampCommon = require('js/pages/timestamp-common.js');  // website/static/js/pages
timestampCommon.setWebOrAdmin('admin');


$(function () {
    var csrftoken = $('[name=csrfmiddlewaretoken]').val()
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
            urlVerify: urls.verify
        });
    };

    var btnAddtimestamp_onclick = function () {
        if ($('#btn-verify').attr('disabled') !== undefined || $('#btn-addtimestamp').attr('disabled') !== undefined) {
            return false;
        }
        timestampCommon.add({
            url: urls.addTimestampData,
        });
    };

    var updatePaginationElements = function () {
        // Page info
        var currentPage = $('.listjs-pagination .active a').text();
        var numPages = $('.listjs-pagination li a').last().text();
        $('.pagination .current').text('Page ' + currentPage + ' of ' + numPages);

        // Enable/disable buttons
        $('#first-page').removeClass('disabled');
        $('#previous-page').removeClass('disabled');
        $('#last-page').removeClass('disabled');
        $('#next-page').removeClass('disabled');
        if (!currentPage || currentPage === '1') {
            $('#first-page').addClass('disabled');
            $('#previous-page').addClass('disabled');
        }
        if (currentPage === numPages) {
            $('#last-page').addClass('disabled');
            $('#next-page').addClass('disabled');
        }
    };

    $('#first-page').on('click', function () {
        $('.listjs-pagination li').first().click();
        updatePaginationElements();
    });

    $('#previous-page').on('click', function () {
        $('.pagination-prev').click();
        updatePaginationElements();
    });

    $('#next-page').on('click', function () {
        $('.pagination-next').click();
        updatePaginationElements();
    });

    $('#last-page').on('click', function () {
        $('.listjs-pagination li').last().click();
        updatePaginationElements();
    });

    $('#pageLength-10').on('click', function () {
        $('#pageLength').val(10).change();
        updatePaginationElements();
    });

    $('#pageLength-25').on('click', function () {
        $('#pageLength').val(25).change();
        updatePaginationElements();
    });

    $('#pageLength-50').on('click', function () {
        $('#pageLength').val(50).change();
        updatePaginationElements();
    });

    $(document).ready(function () {
        timestampCommon.init(urls.taskStatusUrl);
        $('#btn-verify').on('click', btnVerify_onclick).focus();
        $('#btn-addtimestamp').on('click', btnAddtimestamp_onclick).focus();
        $('#btn-cancel').on('click', function () {
            timestampCommon.cancel(urls.cancel);
        }).focus();
        $('#btn-download').on('click', function () {
            timestampCommon.download(urls.downloadErrors);
        });
        updatePaginationElements();
    });
});
