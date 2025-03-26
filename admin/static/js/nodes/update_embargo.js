$(document).ready(function() {
    $("#embargo-update-form").on("submit", function (event) {
        event.preventDefault();

        $("#date-validation").text('');
        $('#update-embargo-modal').modal('show');
    });

    $("#update-embargo-modal").on("submit", function (event) {
        event.preventDefault();

        $(this).modal("hide");

        $.ajax({
            url: window.templateVars.updateEmbargoUrl,
            type: "post",
            data: $("#embargo-update-form").serialize(),
        }).success(function (response) {
            // reload page only after successfull response
            // so errors can be displayed in case of fail
            location.reload();
        }).fail(function (jqXHR, textStatus, error) {
            $("#date-validation").text(jqXHR.responseText);
        });
    });

    $("#datepicker").datepicker({
        format: "mm/dd/yyyy",
        startDate: "+0d"
    })
});
