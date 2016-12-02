"use_strict";

require('bootstrap');
require('jquery');
require('c3/c3.css');

var c3 = require('c3/c3.js');
var keen = require('keen-js');
var ss = require('simple-statistics');


var client = new Keen({
    projectId: keenProjectId,
    readKey : keenReadKey
});


Keen.ready(function () {

    // Active user count!
    var active_user_count = new Keen.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.active",
        timeframe: "previous_1_days",
        timezone: "UTC"
    });

    client.draw(active_user_count, document.getElementById("active-user-count"), {
        chartType: "metric",
        height: "auto",
        width: "auto",
        title: ' '
    });

    // Active user chart!
    var active_user_chart = new Keen.Query("sum", {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.active",
        timeframe: "previous_800_days",
        timezone: "UTC"
    });

    client.draw(active_user_chart, document.getElementById("active-user-chart"), {
        chartType: "linechart",
        height: "auto",
        width: "auto",
        title: ' '
    });

    // Affiliated Public Projects!
    var affiliated_public_chart = new Keen.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "nodes.public",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });

    client.draw(affiliated_public_chart, document.getElementById("affiliated-public-projects"), {
        chartType: "table",
        height: "auto",
        width: "auto",
        title: ' '
    });

    // Yesterday's Node Logs!
    var logs_by_user = new Keen.Query("count", {
        eventCollection: "node_log_events",
        interval: "hourly",
        groupBy: "user_id",
        timeframe: "previous_1_days",
        timezone: "UTC"
    });
    client.draw(logs_by_user, document.getElementById("yesterdays-node-logs-by-user"), {
        chartType: "linechart",
        title: '',
        height: "auto",
        width: "auto"
    });

    // Registrations by Email Domain
    var email_domains = new Keen.Query("count", {
        eventCollection: "user_domain_events",
        groupBy: [
            "domain"
        ],
        interval: "daily",
        timeframe: "previous_7_days",
        timezone: "UTC"
    });

    client.draw(email_domains, document.getElementById("user-registration-by-email-domain"), {
        chartType: "linechart",
        height: "auto",
        width: "auto",
        title: ' '
    });

});
