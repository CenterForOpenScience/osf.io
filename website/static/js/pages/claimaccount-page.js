/**
 * Reset Password page
 */
'use strict';
var $ = require('jquery');

var setPassword = require('js/setPassword');


$(document).ready(function() {
    new setPassword('#setPasswordForm', 'reset');
});
