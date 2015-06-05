/*
* Affixes menu resize with menu and have constant width when scrolling
 */
function fixAffixWidth() {
    $('.affix, .affix-top, .affix-bottom').each(function (){
        var el = $(this);
        var colsize = el.parent('.affix-parent').width();
        el.outerWidth(colsize);
    });
}


$(document).ready(function() {
    $(window).resize(function (){ fixAffixWidth(); });
    $('.affix-menu .panel').on('affixed.bs.affix', function(){ fixAffixWidth();});
});
