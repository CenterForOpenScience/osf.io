'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers.js');
var accountSettings = require('js/accountSettings.js');

$(function() {
    var viewModel = new accountSettings.UserProfileViewModel();
    $osf.applyBindings(viewModel, '#connectedEmails');
    viewModel.init();

    $osf.applyBindings(
        new accountSettings.DeactivateAccountViewModel(),
        '#deactivateAccount'
    );

    $osf.applyBindings(
        new accountSettings.ExportAccountViewModel(),
        '#exportAccount'
    );
});

// Reusable function to fix affix widths to columns.
function fixAffixWidth() {
    $('.affix, .affix-top, .affix-bottom').each(function (){
        var el = $(this);
        var colsize = el.parent('.affix-parent').width();
        el.outerWidth(colsize);
    });
}

$(document).ready(function () {

    $(window).resize(function (){ fixAffixWidth(); });
    $('#affix-nav').on('affixed.bs.affix', function(){ fixAffixWidth(); });

  });
