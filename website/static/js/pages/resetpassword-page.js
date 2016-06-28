/**
 * Reset Password page
 */
'use strict';
var $ = require('jquery');

var SetPassword = require('js/setPassword');
var verificationKey = window.contextVars.verification_key;
var resetUrl = '/resetpassword/' + verificationKey + '/';


$(document).ready(function() {
    new SetPassword('#resetPasswordForm', 'reset', resetUrl, '');
});
