"use_strict";


var keen = require('keen-js');


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
