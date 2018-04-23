'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootstrap = require('bootstrap');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var $osf = require('js/osfHelpers');

/**************************************
* Delete user Key Info                *
***************************************/
$('.is_deleted input').on('click', function() {
    var $input = $(this);
    var institutionId = $input.data('institution-id');
    var userId = $input.data('userid');
    var url = '/keymanagement/' + institutionId + '/delete/' + userId;
    $input.prop('disabled', true);
    $.ajax({
        url: url,
        type: 'GET'
    })
    .done(function(data) {
        return
    })
    .fail(function(xhr, status, error) {
        $input.prop('disabled', false);
        bootbox.alert({
            message: error,
            backdrop: true
        });
    });
});

