/**
 * On page load focus on email input element
 */

var $ = require('jquery');
var ForgotPassword = require('../forgotPassword.js');

new ForgotPassword('#forgotPasswordForm', true);

$( document ).ready(function() {
    $('[name="forgot_password-email"]').focus();
});