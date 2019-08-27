'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');

var confirmed = false;

$('#region_form').submit(function () {
    if (!confirmed) {
        $osf.confirmDangerousAction({
            title: 'Are you sure you want to change institutional storage?',
            message: '<p>The previous storage will no longer be available to all contributors on the project.</p>',
            callback: function () {
                confirmed = true;
                $('#region_form').submit();
            },
            buttons: {
                success: {
                    label: 'Change'
                }
            }
        });
    }
    return confirmed;
});
