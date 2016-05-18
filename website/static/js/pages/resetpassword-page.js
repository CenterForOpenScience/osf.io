/**
 * Reset Password page
 */
'use strict';
var $ = require('jquery');

var SetPassword = require('js/setPassword');
var verificationKey = window.contextVars.verification_key;
var resetUrl = '/api/v1/resetpassword/' + verificationKey + '/';
var redirectrUrl = '/login/';


$(document).ready(function() {
    new SetPassword('#resetPasswordForm', 'reset', resetUrl, '', redirectrUrl);
});
