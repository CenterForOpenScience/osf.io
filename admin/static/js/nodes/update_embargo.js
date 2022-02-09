$(document).ready(function() {
    $("#embargo-update-form").submit(function (event) {
        event.preventDefault();
        $('#update-embargo-modal').modal('show');
    });

    $("#embargo-update-modal").submit(function (event) {
        var data = $('#embargo-update-form').serialize();
        data["validation_only"]="False";
        $.ajax({
            url: window.templateVars.updateEmbargoUrl,
            type: "post",
            data: data,
            success: function (response) {
                location.reload();
            }
        }).fail(function (jqXHR, textStatus, error) {
            $("#date-validation").text(jqXHR.responseText);
        });
    });

    $("#datepicker").datepicker({
        format: "mm/dd/yyyy",
        startDate: "+0d"
    })
        .on("change", function (e) {
            $("#embargo-update-submit").prop('disabled', false);
            $("#date-validation").text('');
            var data = $('#embargo-update-form').serialize();
            data["validation_only"]="True";
            $.ajax({
                url: window.templateVars.updateEmbargoUrl,
                type: "post",
                data: data
            }).fail(function (jqXHR, textStatus, error) {
                $("#date-validation").text(jqXHR.responseText);
                $("#embargo-update-submit").prop('disabled', true);
            });
        });
});
