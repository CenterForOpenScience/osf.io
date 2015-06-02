var profile = require('../profile.js');

var ctx = window.contextVars;

new profile.Names('#names', ctx.nameUrls, ['edit']);
new profile.Social('#social', ctx.socialUrls, ['edit']);
new profile.Jobs('#jobs', ctx.jobsUrls, ['edit']);
new profile.Schools('#schools', ctx.schoolsUrls, ['edit']);

//Fixes profile settings side menu to left column
function fixAffixWidth() {
    $('.affix, .affix-top, .affix-bottom').each(function (){
        var el = $(this);
        var colsize = el.parent('.affix-parent').width();
        el.outerWidth(colsize);
    });
}


$(document).ready(function() {
    $(window).resize(function (){ fixAffixWidth(); });
    $('.profile-page .panel').on('affixed.bs.affix', function(){ fixAffixWidth();});
});



