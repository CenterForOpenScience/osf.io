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
            $("#version-validation").text(jqXHR.responseText);
        });
    });
});
