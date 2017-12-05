require('bootstrap-colorpicker');
require('bootstrap-colorpicker/dist/css/bootstrap-colorpicker.min.css');

//TODO: Consider using pikaday range picker instead

$(document).ready(function() {

    $('#show-modify-form').click(function() {

        $('#table-view').toggle();
        $('#form-view').toggle();

        var text = $('#show-modify-form').text();
        var new_text = (text.trim() == "Modify banner") ? "Hide Form" : "Modify banner";
        $('#show-modify-form').text(new_text);
    });

    $(".datepicker").datepicker({
        format: "mm/dd/yyyy",
        startDate: "+0d"
    });

    $(".colorpicker").colorpicker();

});
