require('bootstrap-colorpicker');
require('bootstrap-colorpicker/dist/css/bootstrap-colorpicker.min.css');

var rdmGettext = require('js/rdmGettext');
var gt = rdmGettext.rdmGettext();
var _ = function(msgid) { return gt.gettext(msgid); };
var agh = require('agh.sprintf');

//TODO: Consider using pikaday range picker instead

$(document).ready(function() {

    $('#show-modify-form').click(function() {

        $('#table-view').toggle();
        $('#form-view').toggle();

        var text = $('#show-modify-form').text();
        var new_text = (text.trim() == "Modify banner") ? _("Hide Form") : _("Modify banner");
        $('#show-modify-form').text(new_text);
    });

    var blackoutDates = JSON.parse($('#blackout-dates')[0].value);

    $(".datepicker").datepicker({
        format: "mm/dd/yyyy",
        startDate: "+0d",
        beforeShowDay: function(date){
            var string = $.datepicker.formatDate('yy-mm-dd', date);
            return [ blackoutDates.indexOf(string) === -1];
        }
    });

    $(".colorpicker").colorpicker();

});
