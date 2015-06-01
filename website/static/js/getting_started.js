'use strict';

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
    $('.scrollspy').on('affixed.bs.affix', function(){ fixAffixWidth(); });

  });
