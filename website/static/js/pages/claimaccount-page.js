/**
 * Reset Password page
 */
'use strict';
var $ = require('jquery');

var setPassword = require('js/resetPassword');


$(document).ready(function() {
    new setPassword('#setPasswordForm');
});
