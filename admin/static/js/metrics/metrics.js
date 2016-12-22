require('c3/c3.css');
require('keen-dataviz/dist/keen-dataviz.min.css');


var c3 = require('c3/c3.js');
var keen = require('keen-js');
var keenDataviz = require('keen-dataviz');
var keenAnalysis = require('keen-analysis');


var client = new keenAnalysis({
    projectId: keenProjectId,
    readKey: keenReadKey
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

    if (metric.params.timeframe.start) {

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

    } else {
        title = metric.params.timeframe;
    }


    return title;
};


var differenceGrowthBetweenMetrics = function(metric1, metric2, totalMetric, element) {
    var percentOne;
    var percentTwo;
    var differenceMetric = new keenDataviz()
        .el(element)
        .chartType("metric")
        .chartOptions({
            suffix: '%'
        })
        .title(' ')
        .prepare();

    client.run([
        metric1,
        metric2,
        totalMetric
    ]).then(function(res) {
        var metricOneResult = res[0].result;
        var metricTwoResult = res[1].result;
        var totalResult = res[2].result;

        percentOne = (metricOneResult/totalResult)*100;
        percentTwo = (metricTwoResult/totalResult)*100;

        var data = {
            "result": percentOne - percentTwo
        };

        differenceMetric.parseRawData(data).render();
    }).catch(function(err) {
        differenceMetric.message(err.message);
    });
};


var renderPublicPrivatePercent = function(publicMetric, privateMetric, element) {
    var result;
    var differenceMetric = new keenDataviz()
        .el(element)
        .type("pie")
        .title(' ')
        .prepare();

    client.run([
        publicMetric,
        privateMetric,
    ], function(err, res) {

        result = [
            {'result': res[0].result, 'label': 'public'}, {'result': res[1].result, 'label': 'private'}
        ];

        var data = {
            "result": result
        };

        differenceMetric.parseRawData(data).render();
    });
};


var renderCalculationBetweenTwoQueries = function(query1, query2, element, differenceType, calculationType) {
    var result;
    var differenceMetric;

    if (calculationType === "percentage") {
        differenceMetric = new keenDataviz()
            .el(element)
            .type("metric")
            .title(' ')
            .chartOptions({
                suffix: '%'
            })
            .prepare();
    } else {
        differenceMetric = new keenDataviz()
            .el(element)
            .chartType("metric")
            .title(' ')
            .prepare();
    }

    differenceMetric.title(getMetricTitle(query1, differenceType));

    client.run([
        query1,
        query2
    ]).then(function(res) {
        var metricOneResult = res[0].result;
        var metricTwoResult = res[1].result;
        // debugger;
        if (calculationType === "subtraction") {
            result = metricOneResult - metricTwoResult;
        } else if (calculationType === "percentage") {
            result = (metricOneResult/metricTwoResult) * 100;
        }

        var data = {
            "result": result
        };

        differenceMetric.parseRawData(data).render();
    })
    .catch(function(err){
        differenceMetric.message(err.message);
    });
};

var getWeeklyUserGain = function() {
    var queries = [];
    var timeframes = [];

    for (i = 3; i < 12; i++) {
        var timeframe = getOneDayTimeframe(i, null);
        var query = new keenAnalysis.Query("sum", {
            eventCollection: "user_summary",
            targetProperty: "status.active",
            timeframe: timeframe
        });
        queries.push(query);
        timeframes.push(timeframe);
    }

    return {"queries": queries, "timeframes": timeframes};

};

keenAnalysis.ready(function(){

    var renderNodeLogsForOneUserChart = function(user_id) {
        var chart = new keenDataviz()
            .el('#yesterdays-node-logs-by-user')
            .height(300)
            .title('Individual Logs for ' + '<a href=../users/' + user_id + '>' + user_id + '/</a>')
            .type('line')
            .prepare();

        client
            .query('count', {
                event_collection: "node_log_events",
                interval: "hourly",
                group_by: "action",
                filters: [{
                    property_name: 'user_id',
                    operator: 'eq',
                    property_value: user_id
                }],
                timeframe: "previous_1_days",
                timezone: "UTC"
            })
            .then(function(res){
                chart
                    .data(res)
                    .render();
            })
            .catch(function(err){
                chart.message(err.message);
            });
    };


    var renderNodeLogsPerUserChart = function() {
        var chart = new keenDataviz()
            .el('#yesterdays-node-logs-by-user')
            .title(' ')
            .chartOptions({
                data: {
                    onclick: function (d, element) {
                        renderNodeLogsForOneUserChart(d.name);
                    }
                }
            })

            .type('line')
            .prepare();

        client
            .query('count', {
                event_collection: 'node_log_events',
                group_by: "user_id",
                timeframe: 'previous_1_days',
                interval: 'hourly'
            })
            .then(function (res) {
                var chartWithData = chart.data(res);
                chartWithData.dataset.filterColumns(function (column, index) {
                    var logThreshhold = 25;
                    for (var i = 0; i < column.length; i++) {
                        if (column[i] > logThreshhold && column[0] != 'null') {
                            return column;
                        }
                    }
                });

                chartWithData.render();
            })
            .catch(function (err) {
                chart.message(err.message);
            });
    };
    renderNodeLogsPerUserChart();

    $('#reload-node-logs')[0].onclick = function() {
        renderNodeLogsPerUserChart();
    };

    //                        _      _
    //  _  _ ___ ___ _ _   __| |__ _| |_ __ _
    // | || (_-</ -_) '_| / _` / _` |  _/ _` |
    //  \_,_/__/\___|_|   \__,_\__,_|\__\__,_|

    var renderKeenMetric = function(element, type, query) {
        var chart = new keenDataviz()
            .el(element)
            .height(400)
            .title(' ')
            .type(type)
            .prepare();

        client
            .run(query)
            .then(function(res){
                chart
                    .data(res)
                    .render();
            })
            .catch(function(err){
                chart.message(err.message);
            });
    };

    // Active user count! - Total Confirmed Users of the OSF
    var activeUsersQuery = new keenAnalysis.Query("sum",  {
        event_collection: "user_summary",
        target_property: "status.active",
        timeframe: "previous_1_days",
        timezone: "UTC"
    });
    renderKeenMetric("#active-user-count", "metric", activeUsersQuery);


    // Daily Active Users
    var dailyActiveUsersQuery = new keenAnalysis.Query("count_unique", {
        event_collection: "pageviews",
        target_property: "user.id",
        timeframe: "previous_1_days",
        timezone: "UTC"

    });
    renderKeenMetric("#daily-active-users", "metric", dailyActiveUsersQuery);

    // Daily Active Users / Total Users
    renderCalculationBetweenTwoQueries(dailyActiveUsersQuery, activeUsersQuery, "#daily-active-over-total-users", null, "percentage");


    // Monthly Active Users
    var monthlyActiveUsersQuery = new keenAnalysis.Query("count_unique" , {
        eventCollection: "pageviews",
        targetProperty: "user.id",
        timeframe: "previous_1_months",
        timezone: "UTC"
    });
    renderKeenMetric("#monthly-active-users", "metric", monthlyActiveUsersQuery);


    // Monthly Active Users / Total Users
    renderCalculationBetweenTwoQueries(monthlyActiveUsersQuery, activeUsersQuery, "#monthly-active-over-total-users", null, 'percentage');


    // Monthly Growth of MAU% -- Two months ago vs 1 month ago
    var twoMonthsAgoActiveUsersQuery = new keenAnalysis.Query("count_unique", {
        eventCollection: "pageviews",
        targetProperty: "user.id",
        timeframe: "previous_2_months",
        timezone: "UTC"
    });
    differenceGrowthBetweenMetrics(twoMonthsAgoActiveUsersQuery, monthlyActiveUsersQuery, activeUsersQuery, "#monthly-active-user-increase", 'day', 'subtraction');

    // Yearly Active Users
    var yearlyActiveUsersQuery = new keenAnalysis.Query("count_unique", {
        eventCollection: "pageviews",
        targetProperty: "user.id",
        timeframe: "previous_1_years",
        timezone: "UTC"
    });
    renderKeenMetric("#yearly-active-users", "metric", yearlyActiveUsersQuery);


    // Yearly Active Users / Total Users
    renderCalculationBetweenTwoQueries(yearlyActiveUsersQuery, activeUsersQuery, "#yearly-active-over-total-users", null, 'percentage');

    // Daily Gain
    var yesterday_user_count = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.active",
        timeframe: getOneDayTimeframe(1, null)
    });

    var two_days_ago_user_count = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.active",
        timeframe: getOneDayTimeframe(2, null)
    });

    renderCalculationBetweenTwoQueries(yesterday_user_count, two_days_ago_user_count, "#daily-user-increase", 'day', 'subtraction');

    // Monthly Gain
    var last_month_user_count = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.active",
        timeframe: getOneDayTimeframe(null, 1)
    });

    var two_months_ago_user_count = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
       targetProperty: "status.active",
        timeframe: getOneDayTimeframe(null, 2)
    });

    renderCalculationBetweenTwoQueries(last_month_user_count, two_months_ago_user_count, "#monthly-user-increase", 'month', 'subtraction');

    var weeklyUserGain = getWeeklyUserGain();

    //  Weekly User Gain metric
    var renderAverageUserGainMetric = function(results) {

        var userGainChart = new keenDataviz()
            .el("#average-gain-metric")
            .type("metric")
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

        var userGainChart = new keenDataviz()
            .el("#user-gain-chart")
            .type("line")
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

    // stickiness ratio - DAU/MAU
    renderCalculationBetweenTwoQueries(dailyActiveUsersQuery, monthlyActiveUsersQuery, "#stickiness-ratio", null, "percentage");


    // Active user chart!
    var activeUserChartQuery = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.active",
        timeframe: "previous_800_days",
        timezone: "UTC"
    });
    renderKeenMetric("#active-user-chart", "line", activeUserChartQuery);


    // New Unconfirmed Users - # of unconfirmed users in the past 7 days
    var yesterday_unconfirmed_user_count = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.unconfirmed",
        timeframe: getOneDayTimeframe(1, null)
    });

    var week_ago_user_count = new Keen.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.unconfirmed",
        timeframe: getOneDayTimeframe(7, null)
    });
    renderCalculationBetweenTwoQueries(yesterday_unconfirmed_user_count, week_ago_user_count, "#unverified-new-users", 'day', 'subtraction');

    // Institutional Users over past 100 Days
    var institutional_user_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        interval: "daily",
        targetProperty: "users.total",
        groupBy: ["institution.name"],
        timeframe: "previous_100_days",
        timezone: "UTC"
    });
    // renderKeenMetric("#institution-growth", "line", institutional_user_chart);


    // Total Institutional Users
    var institutional_user_count = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "users.total",
        timeframe: "previous_1_day",
        timezone: "UTC"
    });
    renderKeenMetric("#total-institutional-users", "metric", institutional_user_count);

    // Total Instutional Users / Total OSF Users
    renderCalculationBetweenTwoQueries(institutional_user_count, activeUsersQuery, "#percentage-institutional-users", null, 'percentage');


    //                _        _
    //  _ __ _ _ ___ (_)___ __| |_ ___
    // | '_ \ '_/ _ \| / -_) _|  _(_-<
    // | .__/_| \___// \___\__|\__/__/
    // |_|         |__/

    // Affiliated Public Nodes
    var affiliated_public_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "nodes.public",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    // renderKeenMetric("#affiliated-public-nodes", "pie", affiliated_public_chart);


    // Affiliated Private Nodes
    var affiliated_private_node_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "nodes.private",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    // renderKeenMetric("#affiliated-private-nodes", "pie", affiliated_private_node_chart);


    // Affiliated Public Registrations
    var affiliated_public_registered_nodes_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "registered_nodes.public",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    // renderKeenMetric("#affiliated-public-registered-nodes", "pie", affiliated_public_registered_nodes_chart);

    // Affiliated Private Registrations
    var affiliated_private_registered_node_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "registered_nodes.private",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    // renderKeenMetric("#affiliated-private-registered-nodes", "pie", affiliated_private_registered_node_chart);


    // Registrations by Email Domain
    var email_domains = new keenAnalysis.Query("count", {
        eventCollection: "user_domain_events",
        groupBy: "domain",
        interval: "daily",
        timeframe: "previous_7_days",
        timezone: "UTC"
    });

    var renderEmailDomainsChart = function() {
        var chart = new keenDataviz()
            .el('#user-registration-by-email-domain')
            .title(' ')
            .type('line')
            .prepare();

        client.run(email_domains)
            .then(function (res) {
                var chartWithData = chart.data(res);
                chartWithData.dataset.filterColumns(function (column, index) {
                    var emailThreshhold = 1;
                    for (var i = 0; i < column.length; i++) {
                        if (column[i] > emailThreshhold) {
                            return column;
                        }
                    }
                });

                chartWithData.render();
            })
            .catch(function (err) {
                chart.message(err.message);
            });
    };
    renderEmailDomainsChart();


    // Previous 7 Days of Users by Status
    var previous_week_active_users = new keenAnalysis.Query("sum",  {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.active",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_unconfirmed_users = new keenAnalysis.Query("sum",  {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.unconfirmed",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_merged_users = new keenAnalysis.Query("sum",  {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.merged",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_depth_users = new keenAnalysis.Query("sum",  {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.depth",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_deactivated_users = new keenAnalysis.Query("sum",  {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.deactivated",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var chart = new keenDataviz()
        .el("#previous-7-days-of-users-by-status")
        .type("line")
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

    //                                   _
    //  _ _ __ ___ __ __  _ _ _  _ _ __ | |__  ___ _ _ ___
    // | '_/ _` \ V  V / | ' \ || | '  \| '_ \/ -_) '_(_-<
    // |_| \__,_|\_/\_/  |_||_\_,_|_|_|_|_.__/\___|_| /__/
    //
    var renderProjectNodeMetrics = function() {
        var propertiesAndElements = {
            'projects.total': '#total-projects',
            'projects.public': '#public-projects',
            'projects.private': '#private-projects',
            'nodes.total': '#total-nodes',
            'nodes.public': '#public-nodes',
            'nodes.private': '#private-nodes',
            'registered_projects.total': '#total-registered-projects',
            'registered_projects.public': '#public-registered-projects',
            'registered_projects.embargoed': '#embargoed-registered-projects',
            'registered_nodes.total': '#total-registered-nodes',
            'registered_nodes.public': '#public-registered-nodes',
            'registered_nodes.embargoed': '#embargoed-registered-nodes'
        };

        var graphPromises = [];
        for (var key in propertiesAndElements) {
            if (propertiesAndElements.hasOwnProperty(key)) {
                graphPromises.push(client.query('sum', {
                    event_collection: "node_summary",
                    target_property: key,
                    timeframe: "previous_1_days",
                    timezone: "UTC"
                }))
            }
        }

        var results = Promise.all(graphPromises).then(function(values) {
            for (var i=0; i<values.length; i++) {
                var chart = new keenDataviz()
                    .el(propertiesAndElements[values[i].query.target_property])
                    .height(300)
                    .title(' ')
                    .type('metric')
                    .prepare();

                chart.data(values[i]).render();

            }

        });

    };
    renderProjectNodeMetrics();


 //          _    _
 //  __ _ __| |__| |___ _ _  ___
 // / _` / _` / _` / _ \ ' \(_-<
 // \__,_\__,_\__,_\___/_||_/__/
 //

    // Previous 7 days of linked addon by addon name
    var linked_addon = new keenAnalysis.Query("sum", {
        eventCollection: "addon_snapshot",
        targetProperty: "users.linked",
        groupBy: ["provider.name"],
        interval: "daily",
        timeframe: "previous_8_days",
        timezone: "UTC"
    });
    renderKeenMetric('#previous-7-days-of-linked-addon-by-addon-name', "line", linked_addon);


});
