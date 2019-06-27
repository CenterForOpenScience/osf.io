'use strict';

var $ = require('jquery');

$('.next-btn').click(function () {
    var selectedProvider = $('input[name=\'options\']:checked').val();
    switch (selectedProvider) {
        default:
            $('#sample_modal').modal('show');
            break;
    }
});
