'use strict';

var $ = require('jquery');

$('.next-btn').click(function () {
    var selectedProvider = $('input[name=\'options\']:checked').val();
    $('#' + selectedProvider + '_modal').modal('show');
});
