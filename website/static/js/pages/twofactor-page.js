/**
 * On page load focus on two factor input element
 */

var $ = require('jquery');

$( document ).ready(function() {
    $('[name="twoFactorCode"]').focus();
});