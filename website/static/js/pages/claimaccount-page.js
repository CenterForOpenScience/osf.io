/**
 * Reset Password page
 */
'use strict';
var $ = require('jquery');

var passwordForms = require('js/passwordForms');


$(document).ready(function() {
    new passwordForms.SetPassword('#setPasswordForm');
});
