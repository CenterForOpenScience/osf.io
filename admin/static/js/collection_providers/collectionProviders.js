$(document).ready(function() {
    $("#show-modify-form").click(function() {
        $("#table-view").toggle();
        $("#form-view").toggle();

        var text = $("#show-modify-form").text();
        var new_text = (text.trim() == "Modify Collection Provider") ? "Hide Form" : "Modify Collection Provider";
        $("#show-modify-form").text(new_text);
    });
});