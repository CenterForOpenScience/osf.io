require('c3/c3.css');

var c3 = require('c3/c3.js');
var keen = require('keen-js');

var client = new Keen({
    projectId: keenProjectId,
    readKey : keenReadKey
});


var getOneDayTimeframe = function(daysBack, monthsBack) {
    var start = null;
    var end = null;
    var today = new Date();

    today.setMonth(today.getMonth() - monthsBack);
    if (daysBack) {
        today.setUTCDate(today.getDate() - daysBack);
    } else {
        today.setUTCDate(1);
    }
    today.setUTCHours(0, 0, 0, 0, 0);
    start = today.toISOString();
    today.setDate(today.getDate() + 1);
    end = today.toISOString();
    return {
        "start": start,
        "end": end
    };
};



/**
 * Configure a Title for a chart dealing with the past month or day
 *
 * @method getMonthTitle
 * @param {Object} metric - metric result object to get the date from
 * @return {String} the title for the monthly metric chart
 */
var getMetricTitle = function(metric, type) {
    var monthNames = ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];
    var date = null;
    var end = null;
    var title = null;

    if (type === "month") {
        date = new Date(metric.params.timeframe.start);
        title =  monthNames[date.getUTCMonth()] + " to " + monthNames[date.getUTCMonth() + 1];
    } else if (type === "day") {
        date = metric.params.timeframe.start.replace('T00:00:00.000Z', '');
        end = metric.params.timeframe.end.replace('T00:00:00.000Z', '');
        title =  date + " until " + end;
    }

    return title;
};


var renderCalculationBetweenTwoMetrics = function(metric1, metric2, element, differenceType, calculationType) {
    var result;
    var differenceMetric;

    if (calculationType === "percentage") {
        differenceMetric = new Keen.Dataviz()
            .el(document.getElementById(element))
            .chartType("metric")
            .title(' ')
            .chartOptions({
                suffix: '%'
            })
            .prepare();
    } else {
        differenceMetric = new Keen.Dataviz()
            .el(document.getElementById(element))
            .chartType("metric")
            .title(' ')
            .prepare();
    }

    differenceMetric.title(getMetricTitle(metric1, differenceType));

    client.run([
        metric1,
        metric2
    ], function(err, res) {
        var metricOneResult = res[0].result;
        var metricTwoResult = res[1].result;

        if (calculationType === "subtraction") {
            result = metricOneResult - metricTwoResult;
        } else if (calculationType === "percentage") {
            result = (metricOneResult/metricTwoResult) * 100;
        }

        var data = {
            "result": result
        };

        differenceMetric.parseRawData(data).render();
    });
};

var getWeeklyUserGain = function() {
    var queries = [];
    var timeframes = [];

    for (i = 3; i < 12; i++) {
        var timeframe = getOneDayTimeframe(i, null);
        var query = new Keen.Query("sum", {
            eventCollection: "user_summary",
            targetProperty: "status.active",
            timeframe: timeframe
        });
        queries.push(query);
        timeframes.push(timeframe);
    }

    return {"queries": queries, "timeframes": timeframes}

};

Keen.ready(function () {

    //  _  _ ___ ___ _ _ ___
    // | || (_-</ -_) '_(_-<
    //  \___/__/\___|_| /__/

    // Active user count!
    var active_user_count = new Keen.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.active",
        timeframe: "previous_2_days",
        timezone: "UTC"
    });

    client.draw(active_user_count, document.getElementById("active-user-count"), {
        chartType: "metric",
        height: "auto",
        width: "auto",
        chartOptions: {
            legend: {position: "top"}
        },
        title: ' '
    });

    // Daily Active Users
    var daily_active_users = new Keen.Query("count_unique", {
        eventCollection: "pageviews",
        targetProperty: "user.id",
        timeframe: "previous_1_days",
        timezone: "UTC"
    });

    client.draw(daily_active_users, document.getElementById("daily-active-users"), {
        chartType: "metric",
        title: ' '
    });

    // Daily Active Users / Total Users
    renderCalculationBetweenTwoMetrics(daily_active_users, active_user_count, "daily-active--over-total-users", null, 'percentage');

    // Daily Gain
    var yesterday_user_count = new Keen.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.active",
        timeframe: getOneDayTimeframe(3, null)
    });

    var two_days_ago_user_count = new Keen.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.active",
        timeframe: getOneDayTimeframe(4, null)
    });

    renderCalculationBetweenTwoMetrics(yesterday_user_count, two_days_ago_user_count, "daily-user-increase", 'day', 'subtraction');

    // Monthly Gain
    var last_month_user_count = new Keen.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.active",
        timeframe: getOneDayTimeframe(null, 1)
    });

    var two_months_ago_user_count = new Keen.Query("sum", {
        eventCollection: "user_summary",
       targetProperty: "status.active",
        timeframe: getOneDayTimeframe(null, 2)
    });

    renderCalculationBetweenTwoMetrics(last_month_user_count, two_months_ago_user_count, "monthly-user-increase", 'month', 'subtraction');

    var weeklyUserGain = getWeeklyUserGain();

    //  Weekly User Gain metric
    var renderAverageUserGainMetric = function(results) {

        var userGainChart = new Keen.Dataviz()
            .el(document.getElementById("average-gain-metric"))
            .chartType("metric")
            .title(' ')
            .prepare();

        client.run(results.queries, function(err, res) {
            var sum = 0;
            for (j = 0; j<res.length - 1; j++) {
                sum += (res[j].result - res[j + 1].result);
            }
            userGainChart.parseRawData({result: sum/(res.length - 1)}).render();
        });

    };
    renderAverageUserGainMetric(weeklyUserGain);

    // User Gain Chart over past 7 days
    var renderWeeklyUserGainChart = function(results) {

        var userGainChart = new Keen.Dataviz()
            .library('c3')
            .el(document.getElementById("user-gain-chart"))
            .chartType("line")
            .title(' ')
            .prepare();

        client.run(results.queries, function(err, res) {
            var data = [];
            for (j = 0; j<res.length - 1; j++) {
                data.push({
                    "value": res[j].result - res[j + 1].result,
                    "timeframe": results.timeframes[j]
                })

            }
            userGainChart.parseRawData({result: data}).render();
        });

    };
    renderWeeklyUserGainChart(weeklyUserGain);

    // Active user chart!
    var active_user_chart = new Keen.Query("sum", {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.active",
        timeframe: "previous_800_days",
        timezone: "UTC"
    });

    client.draw(active_user_chart, document.getElementById("active-user-chart"), {
        chartType: "line",
        library: "c3",
        title: ' '
    });

    //                _        _
    //  _ __ _ _ ___ (_)___ __| |_ ___
    // | '_ \ '_/ _ \| / -_) _|  _(_-<
    // | .__/_| \___// \___\__|\__/__/
    // |_|         |__/

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

    // Affiliated Private Projects!
    var affiliated_private_chart = new Keen.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "nodes.private",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });

    client.draw(affiliated_private_chart, document.getElementById("affiliated-private-projects"), {
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
        chartType: "line",
        library: "c3",
        chartOptions: {
            legend: {
                show: false
            },
            tooltip: {
                grouped: false
            }
        },
        title: ' '
    });

    // Yesterday's Node Logs by User
    var logs_by_user = new Keen.Query("count", {
        eventCollection: "node_log_events",
        interval: "hourly",
        groupBy: "user_id",
        timeframe: "previous_1_days",
        timezone: "UTC"
    });
    client.draw(logs_by_user, document.getElementById("yesterdays-node-logs-by-user"), {
        chartType: "line",
        library: "c3",
        chartOptions: {
            legend: {
                show: false
            },
            tooltip: {
                grouped: false
            }
        },
        title: " "
    });

    // Previous 7 Days of Users by Status
    var previous_week_active_users = new Keen.Query("sum",  {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.active",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_unconfirmed_users = new Keen.Query("sum",  {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.unconfirmed",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_merged_users = new Keen.Query("sum",  {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.merged",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_depth_users = new Keen.Query("sum",  {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.depth",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_deactivated_users = new Keen.Query("sum",  {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.deactivated",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var chart = new Keen.Dataviz()
        .el(document.getElementById("previous-7-days-of-users-by-status"))
        .chartType("line")
        .library("c3")
        .prepare();

    client.run([
        previous_week_active_users,
        previous_week_unconfirmed_users,
        previous_week_merged_users,
        previous_week_depth_users,
        previous_week_deactivated_users
    ], function(err, res) {
        var active_result = res[0].result;
        var unconfirmed_result = res[1].result;
        var merged_result = res[2].result;
        var depth_result = res[3].result;
        var deactivated_result = res[4].result;
        var data = [];
        var i=0;

        while (i < active_result.length) {
            data[i] = {
                timeframe: active_result[i]["timeframe"],
                value: [
                    {category: "Active", result: active_result[i].value},
                    {category: "Unconfirmed", result: unconfirmed_result[i].value},
                    {category: "Merged", result: merged_result[i].value},
                    {category: "Depth", result: depth_result[i].value},
                    {category: "Deactivated", result: deactivated_result[i].value}
                ]
            };
            if (i === active_result.length - 1) {
                chart.parseRawData({result: data}).render();
            }
            i++;
        }
    });

    // Previous 7 days of linked addon by addon name
    var linked_addon = new Keen.Query("sum", {
        eventCollection: "addon_snapshot",
        targetProperty: "users.linked",
        groupBy: [
            "provider.name"
        ],
        interval: "daily",
        timeframe: "previous_8_days",
        timezone: "UTC"
    });

    client.draw(linked_addon, document.getElementById("previous-7-days-of-linked-addon-by-addon-name"), {
        chartType: "linechart",
        chartOptions: {
            legend: {position: "top"}
        },
        title: ' '
    });

});
