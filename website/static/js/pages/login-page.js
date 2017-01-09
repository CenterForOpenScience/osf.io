/**
 * Login page
 */
'use strict';
var $ = require('jquery');

var passwordForms = require('js/passwordForms');

var activateToggleBox = function () {
    var el = $(this);

    if (el.hasClass('toggle-box-muted')) {
        $('.toggle-box-active').removeClass('toggle-box-active').addClass('toggle-box-muted');
        el.removeClass('toggle-box-muted').addClass('toggle-box-active');
    }
};

$(document).ready(function() {
    var campaign = window.contextVars.campaign;
    new passwordForms.SignUp('#signUpScope', campaign);
});

$('.toggle-box').on('click', activateToggleBox);
$('.toggle-box').on('focus', '*', function() {
    activateToggleBox.apply( $(this).parents('.toggle-box') );
});

