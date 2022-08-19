'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');

function restoreExportData() {
    let data = {};
    data["destination_id"]= $("#destination_storage").val();
    $("#restore_button").addClass("disabled");
    $("#stop_restore_button").removeClass("disabled");
    $("#restore_button").attr("disabled", true);
    $("#stop_restore_button").attr("disabled", false);
    $.ajaxSetup({
        data: { csrfmiddlewaretoken: '{{ csrf_token }}' },
    });
    $.ajax({
        url: "restore_export_data",
        type: "post",
        data: data
    }).done(function(response) {
        let task_id = response["task_id"];
        setTimeout(function() {
            checkTaskStatus(task_id);
        }, 1000);
    }).fail(function(jqXHR, textStatus, error) {
        cancelRestore();
    });
}

function checkTaskStatus(task_id){
    let data = { task_id: task_id };
    $.ajaxSetup({
        data: { csrfmiddlewaretoken: '{{ csrf_token }}' },
    });
    $.ajax({
        url: "task_status",
        type: "get",
        data: data
    }).done(function(response) {
        let state = response["state"];
        let result = response["result"];
        if (state === 'SUCCESS' && result === 'Open Dialog') {
            // Open Dialog
            $("#restore").modal('show');
        } else if (state === 'PENDING') {
           setTimeout(function() {
               checkTaskStatus(task_id);
           }, 1000);
        } else {
            cancelRestore();
        }
    }).fail(function(jqXHR, textStatus, error) {
        cancelRestore();
    });
}

function cancelRestore() {
    $("#restore_button").removeClass("disabled");
    $("#stop_restore_button").addClass("disabled");
    $("#restore_button").attr("disabled", false);
    $("#stop_restore_button").attr("disabled", true);
}

function startRestore() {
    $("#restore").modal('hide');
    // Enable "Check export data" button, disable "Stop restoring" button
    $("#check_restore_button").removeClass("disabled");
    $("#stop_restore_button").addClass("disabled");
    $("#check_restore_button").attr("disabled", false);
    $("#stop_restore_button").attr("disabled", true);
}
