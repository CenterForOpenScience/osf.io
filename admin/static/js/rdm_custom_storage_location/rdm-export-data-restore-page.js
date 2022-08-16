'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');

function restoreExportData() {
    let data = {};
    data["destination_id"]= $("#destination_storage").val();
    $("#restoreBtn").addClass("disabled");
    $("#stopRestoreBtn").removeClass("disabled");
    $("#restoreBtn").attr("disabled", true);
    $("#stopRestoreBtn").attr("disabled", false);
    $.ajaxSetup({
        data: { csrfmiddlewaretoken: '{{ csrf_token }}' },
    });
    $.ajax({
        url: "restore_export_data",
        type: "post",
        data: data
    }).done(function(response) {
        let task_id = response["task_id"];
        setTimeout(() => {
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
           setTimeout(() => {
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
    $("#restoreBtn").removeClass("disabled");
    $("#stopRestoreBtn").addClass("disabled");
    $("#restoreBtn").attr("disabled", false);
    $("#stopRestoreBtn").attr("disabled", true);
}

function startRestore() {
    $("#restore").modal('hide');
    // Enable "Check export data" button, disable "Stop restoring" button
    $("#checkRestoreBtn").removeClass("disabled");
    $("#stopRestoreBtn").addClass("disabled");
    $("#checkRestoreBtn").attr("disabled", false);
    $("#stopRestoreBtn").attr("disabled", true);
}
