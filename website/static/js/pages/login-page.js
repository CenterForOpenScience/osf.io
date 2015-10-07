/**
 * Login page
 */
var $ = require('jquery');

var LogInForm = require('js/signIn');
new LogInForm.SignIn('#logInForm');

var SignUp = require('../signUp.js');
new SignUp('#signUpScope', '/api/v1/register/', $('#campaign').val());

var activateToggleBox = function () {
    var el = $(this);

    if (el.hasClass('toggle-box-muted')) {
        $('.toggle-box-active').removeClass('toggle-box-active').addClass('toggle-box-muted');
        el.removeClass('toggle-box-muted').addClass('toggle-box-active');
    }
};

$('.toggle-box').on('click', activateToggleBox);
$('.toggle-box').on('focus', '*', function() {
    activateToggleBox.apply( $(this).parents('.toggle-box') );
});

