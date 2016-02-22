/**
 * Login page
 */
'use strict';
var $ = require('jquery');

var SignUp = require('js/signUp');
var LogInForm = require('js/signIn');
var InstitutionSignIn = require('js/institutionSignIn');

var registerUrl = window.contextVars.registerUrl;


var activateToggleBox = function () {
    var el = $(this);

    if (el.hasClass('toggle-box-muted')) {
        $('.toggle-box-active').removeClass('toggle-box-active').addClass('toggle-box-muted');
        el.removeClass('toggle-box-muted').addClass('toggle-box-active');
    }
};

$(document).ready(function() {
    var campaign = window.contextVars.campaign;
    if (campaign === 'institution'){
        new InstitutionSignIn('#inst');
    } else {
        new LogInForm.SignIn('#logInForm');
        new SignUp('#signUpScope', registerUrl, campaign);
    }
});

$('.toggle-box').on('click', activateToggleBox);
$('.toggle-box').on('focus', '*', function() {
    activateToggleBox.apply( $(this).parents('.toggle-box') );
});

