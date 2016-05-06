/**
 * Reset Password page
 */
'use strict';
var $ = require('jquery');

var SetPassword = require('js/setPassword');


$(document).ready(function() {
    new SetPassword('#resetPasswordForm', 'reset');
});
