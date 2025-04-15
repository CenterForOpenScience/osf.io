$(document).ready(function() {

    $("#confirmReversion").on("submit", function (event) {
        event.preventDefault();

        $.ajax({
            url: window.templateVars.reVersionPreprint,
            type: "post",
            data: $("#re-version-preprint-form").serialize(),
        }).success(function (response) {
            if (response.redirect) {
                window.location.href = response.redirect;
            }
        }).fail(function (jqXHR, textStatus, error) {
            $("#date-validation").text(jqXHR.responseText);
        });
    });

    $(".datepicker").datepicker({
        format: "yyyy-mm-dd",
        startDate: "+0d",
    });

});
