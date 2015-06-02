var profile = require('../profile.js');

var ctx = window.contextVars;

new profile.Names('#names', ctx.nameUrls, ['edit']);
new profile.Social('#social', ctx.socialUrls, ['edit']);
new profile.Jobs('#jobs', ctx.jobsUrls, ['edit']);
new profile.Schools('#schools', ctx.schoolsUrls, ['edit']);

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
