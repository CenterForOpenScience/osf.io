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