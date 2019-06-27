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

$("#swift_keytone_versionSelect").change(function() {
    var swift_keystone_version_val = $(this).val();
    if (swift_keystone_version_val == "v2") {
        $('#swift_project_domain_name').attr('disabled', true);
        $('#swift_user_domain_name').attr('disabled', true);
    } else {
              $('#swift_project_domain_name').attr('disabled', false);
        $('#swift_user_domain_name').attr('disabled', false);
    }
  });

