'use strict';

var $ = require('jquery');

$('.next-btn').click(function () {
    var selectedProvider = $('input[name=\'options\']:checked').val();
    $('#' + selectedProvider + '_modal').modal('show');
});

$('#s3_modal input').keyup(function () {
    // Check if all the inputs are filled, so we can enable the connect button
    var allFilled = $('#s3_modal [required]').toArray().reduce(function (accumulator, current) {
        return accumulator && current.value.length > 0;
    }, true);
    $('#s3_connect').toggleClass('disabled', !allFilled);
});

