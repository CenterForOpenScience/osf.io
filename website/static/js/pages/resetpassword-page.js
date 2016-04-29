/**
 * Reset Password page
 */
'use strict';
var $ = require('jquery');

var ResetPassword = require('js/resetPassword');


$(document).ready(function() {
    new ResetPassword('#resetPasswordForm');
});
