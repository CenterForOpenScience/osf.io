var rdmGettext = require('js/rdmGettext');
var gt = rdmGettext.rdmGettext();
var _ = function(msgid) { return gt.gettext(msgid); };
var agh = require('agh.sprintf');

$(document).ready(function() {
    $("#show-modify-form").click(function() {
        $("#table-view").toggle();
        $("#form-view").toggle();

        var text = $("#show-modify-form").text();
        var new_text = (text.trim() == "Modify Collection Provider") ? _("Hide Form") : _("Modify Collection Provider");
        $("#show-modify-form").text(new_text);
    });
});