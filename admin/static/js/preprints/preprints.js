$(document).ready(function() {

    $("#confirmReversion").on("submit", function (event) {
        event.preventDefault();
        console.log(123);

        $.ajax({
            url: window.templateVars.reVersionPreprint,
            type: "post",
            data: $("#re-version-preprint-form").serialize(),
        }).success(function (response) {
            console.log(response);
        }).fail(function (jqXHR, textStatus, error) {
            $("#date-validation").text(jqXHR.responseText);
        });
    });

    $(".datepicker").datepicker({
        format: "yyyy-mm-dd",
        startDate: "+0d",
    });

});
