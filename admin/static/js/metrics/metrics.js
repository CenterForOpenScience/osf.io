'use strict';

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

var publicClient = new keenAnalysis({
    projectId: keenPublicProjectId,
    readKey: keenPublicReadKey
});

// Heights and Colors for the below rendered
// Keen and c3 Data visualizations
var defaultHeight = 200;
var bigMetricHeight = 350;
var institutionTableHeight = "auto";

var defaultColor = '#00BBDE';
var monthColor = '#0CF5DB';
var yearColor = '#0CEB92';
var dayColor = '#0C93F5';
var privateColor = '#F20066';
var publicColor = '#FFD300';

/**
 * Configure a timeframe for the past day for a keen query
 * Can either be used to get a time frame for one day from today, or one day
 * starting from one month ago.
 *
 * @method getOneDayTimeframe
 * @param {Integer} daysBack - the number of days back to start the one day timeframe
 * @param {Integer} monthsBack - the number of months back to start the one day timeframe
 * @return {Object} the keen-formatted timeframe
 */
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
            title =  monthNames[date.getUTCMonth()] + " to " + monthNames[(date.getUTCMonth() + 1)%12];
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


var differenceGrowthBetweenMetrics = function(metric1, metric2, totalMetric, element, colors) {
    var percentOne;
    var percentTwo;
    var differenceMetric = new keenDataviz()
        .el(element)
        .chartType("metric")
        .chartOptions({
            suffix: '%'
        })
        .title(' ')
        .height(defaultHeight)
        .prepare();

    if (colors) {
        differenceMetric.colors([colors]);
    }

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


var renderCalculationBetweenTwoQueries = function(query1, query2, element, differenceType, calculationType, colors) {
    var result;
    var differenceMetric;

    if (calculationType === "percentage") {
        differenceMetric = new keenDataviz()
            .el(element)
            .type("metric")
            .title(' ')
            .height(defaultHeight)
            .chartOptions({
                suffix: '%'
            })
            .prepare();
    } else {
        differenceMetric = new keenDataviz()
            .el(element)
            .height(defaultHeight)
            .chartType("metric")
            .title(' ')
            .prepare();
    }

    if (colors) {
        differenceMetric.colors([colors]);
    }

    differenceMetric.title(getMetricTitle(query1, differenceType));

    client.run([
        query1,
        query2
    ]).then(function(res) {
        var metricOneResult = res[0].result;
        var metricTwoResult = res[1].result;
        if (calculationType === "subtraction") {
            result = metricOneResult - metricTwoResult;
        } else if (calculationType === "percentage") {
            result = (metricOneResult/metricTwoResult) * 100;
        } else if (calculationType === "division") {
            result = metricOneResult/metricTwoResult;
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

    // get timeframes from 1 day back through 7 days back for the full week
    for (var i = 1; i < 8; i++) {
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

var renderKeenMetric = function(element, type, query, height, colors, keenClient) {

    if (!keenClient) {
        keenClient = client;
    }

    var chart = new keenDataviz()
        .el(element)
        .height(height)
        .title(' ')
        .type(type)
        .prepare();

    if (colors) {
        chart.colors([colors]);
    }

    keenClient
        .run(query)
        .then(function(res){
            var metricChart = chart.data(res);
            metricChart.dataset.sortRows("desc", function(row) {
                return row[1]
            });
            metricChart.render();
        })
        .catch(function(err){
            chart.message(err.message);
        });
};

var renderNodeLogsForOneUserChart = function(user_id) {
    var chart = new keenDataviz()
        .el('#yesterdays-node-logs-by-user')
        .height(bigMetricHeight)
        .title('Individual Logs for ' + '<a href=../users/' + user_id + '>' + user_id + '</a>')
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


// Common Queries

// Active user count! - Total Confirmed Users of the OSF
var activeUsersQuery = new keenAnalysis.Query("sum", {
    event_collection: "user_summary",
    target_property: "status.active",
    timeframe: "previous_1_days",
    timezone: "UTC"
});

// Monthly Active Users
var monthlyActiveUsersQuery = new keenAnalysis.Query("count_unique", {
    eventCollection: "pageviews",
    targetProperty: "user.id",
    timeframe: "previous_1_months",
    timezone: "UTC"
});

var dailyActiveUsersQuery = new keenAnalysis.Query("count_unique", {
    event_collection: "pageviews",
    target_property: "user.id",
    timeframe: "previous_1_days",
    timezone: "UTC"
});

var totalProjectsQuery = new keenAnalysis.Query("sum", {
    eventCollection: "node_summary",
    targetProperty: "projects.total",
    timezone: "UTC",
    timeframe: "previous_1_days",
});

// <+><+><+><+><+><+
//    user data    |
// ><+><+><+><+><+>+

var renderMainCounts = function() {

    // Active user chart!
    var activeUserChartQuery = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.active",
        timeframe: "previous_800_days",
        timezone: "UTC"
    });
    renderKeenMetric("#active-user-chart", "line", activeUserChartQuery, bigMetricHeight);

    renderKeenMetric("#active-user-count", "metric", activeUsersQuery, bigMetricHeight);

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
    renderCalculationBetweenTwoQueries(last_month_user_count, two_months_ago_user_count, "#monthly-user-increase", 'month', 'subtraction', monthColor);

    var week_ago_user_count = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.unconfirmed",
        timeframe: getOneDayTimeframe(7, null)
    });

    // New Unconfirmed Users - # of unconfirmed users in the past 7 days
    var yesterday_unconfirmed_user_count = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        targetProperty: "status.unconfirmed",
        timeframe: getOneDayTimeframe(1, null)
    });
    renderCalculationBetweenTwoQueries(yesterday_unconfirmed_user_count, week_ago_user_count, "#unverified-new-users", 'week', 'subtraction');

};

//  Weekly User Gain metric
var renderAverageUserGainMetric = function (results) {

    var userGainChart = new keenDataviz()
        .el("#average-gain-metric")
        .type("metric")
        .height(defaultHeight)
        .title(' ')
        .prepare();

    client.run(results.queries, function (err, res) {
        var sum = 0;
        for (var j = 0; j < res.length - 1; j++) {
            sum += (res[j].result - res[j + 1].result);
        }
        userGainChart.parseRawData({result: sum / (res.length - 1)}).render();
    });

};

// User Gain Chart over past 7 days
var renderWeeklyUserGainChart = function (results) {

    var userGainChart = new keenDataviz()
        .el("#user-gain-chart")
        .type("line")
        .title(' ')
        .prepare();

    client.run(results.queries, function (err, res) {
        var data = [];
        for (var j = 0; j < res.length - 1; j++) {
            data.push({
                "value": res[j].result - res[j + 1].result,
                "timeframe": results.timeframes[j]
            });
        }
        userGainChart.parseRawData({result: data}).render();
    });
};


// Previous 7 Days of Users by Status
var renderPreviousWeekOfUsersByStatus = function() {

    var previous_week_active_users = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.active",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_unconfirmed_users = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.unconfirmed",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_merged_users = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.merged",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_depth_users = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.depth",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var previous_week_deactivated_users = new keenAnalysis.Query("sum", {
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "status.deactivated",
        timeframe: "previous_1_week",
        timezone: "UTC"
    });

    var chart = new keenDataviz()
        .el("#previous-7-days-of-users-by-status")
        .height(defaultHeight)
        .type("line")
        .prepare();

    client.run([
        previous_week_active_users,
        previous_week_unconfirmed_users,
        previous_week_merged_users,
        previous_week_depth_users,
        previous_week_deactivated_users
    ], function (err, res) {
        var active_result = res[0].result;
        var unconfirmed_result = res[1].result;
        var merged_result = res[2].result;
        var depth_result = res[3].result;
        var deactivated_result = res[4].result;
        var data = [];
        var i = 0;

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
};

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

var NodeLogsPerUser = function() {
    var chart = new keenDataviz()
        .el('#yesterdays-node-logs-by-user')
        .title(' ')
        .height(bigMetricHeight)
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
                    if (column[i] > logThreshhold && column[0] != 'null' && column[0] != 'uj57r') {
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


var UserGainMetrics = function() {
    renderMainCounts();

    var weeklyUserGain = getWeeklyUserGain();

    renderWeeklyUserGainChart(weeklyUserGain);
    renderAverageUserGainMetric(weeklyUserGain);

    renderEmailDomainsChart();
    renderPreviousWeekOfUsersByStatus();

    NodeLogsPerUser();
};


// <+><+><+><+><+><+><+<+>+
//   institution metrics  |
// ><+><+><+><+><+><+><+><+

var InstitutionMetrics = function() {

    // Institutional Users over past 100 Days
    var institutional_user_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        interval: "daily",
        targetProperty: "users.total",
        groupBy: "institution.name",
        timeframe: "previous_100_days",
        timezone: "UTC"
    });
    renderKeenMetric("#institution-growth", "line", institutional_user_chart, 400);


    // Total Institutional Users
    var institutional_user_count = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "users.total",
        timeframe: "previous_1_day",
        timezone: "UTC"
    });
    renderKeenMetric("#total-institutional-users", "metric", institutional_user_count, defaultHeight);

    // Total Instutional Users / Total OSF Users
    renderCalculationBetweenTwoQueries(institutional_user_count, activeUsersQuery, "#percentage-institutional-users", null, 'percentage');

    // Nodes!

    // Affiliated Public Nodes
    var affiliated_public_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "nodes.public",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    renderKeenMetric("#affiliated-public-nodes", "table", affiliated_public_chart, institutionTableHeight);


    // Affiliated Private Nodes
    var affiliated_private_node_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "nodes.private",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    renderKeenMetric("#affiliated-private-nodes", "table", affiliated_private_node_chart, institutionTableHeight);


    // Affiliated Public Registrations
    var affiliated_public_registered_nodes_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "registered_nodes.public",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    renderKeenMetric("#affiliated-public-registered-nodes", "table", affiliated_public_registered_nodes_chart, institutionTableHeight);

    // Affiliated Private Registrations
    var affiliated_private_registered_node_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "registered_nodes.private",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    renderKeenMetric("#affiliated-embargoed-registered-nodes", "table", affiliated_private_registered_node_chart, institutionTableHeight);

    // Projcets!

    // Affiliated Public Projects
    var affiliated_public_projects_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "projects.public",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    renderKeenMetric("#affiliated-public-projects", "table", affiliated_public_projects_chart, institutionTableHeight);


    // Affiliated Private Projects
    var affiliated_private_project_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "projects.private",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    renderKeenMetric("#affiliated-private-projects", "table", affiliated_private_project_chart, institutionTableHeight);


    // Affiliated Public Projects Registrations
    var affiliated_public_registered_projects_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "registered_projects.public",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    renderKeenMetric("#affiliated-public-registered-projects", "table", affiliated_public_registered_projects_chart, institutionTableHeight);

    // Affiliated Private Projects Registrations
    var affiliated_private_registered_projects_chart = new keenAnalysis.Query("sum", {
        eventCollection: "institution_summary",
        targetProperty: "registered_projects.private",
        timeframe: "previous_1_days",
        groupBy: "institution.name",
        timezone: "UTC"
    });
    renderKeenMetric("#affiliated-embargoed-registered-projects", "table", affiliated_private_registered_projects_chart, institutionTableHeight);

};

// <+><+><+><+><+><+><+<+>+
//   active user metrics |
// ><+><+><+><+><+><+><+><+


var ActiveUserMetrics = function() {

    // Recent Daily Unique Sessions
    var recentDailyUniqueSessions = new keenAnalysis.Query("count_unique", {
        eventCollection: "pageviews",
        targetProperty: "visitor.session",
        interval: "daily",
        timeframe: "previous_14_days",
        timezone: "UTC"
    });
    renderKeenMetric("#recent-daily-unique-sessions", "line", recentDailyUniqueSessions, defaultHeight);

    // Daily Active Users
    var dailyActiveUsersQuery = new keenAnalysis.Query("count_unique", {
        event_collection: "pageviews",
        target_property: "user.id",
        timeframe: "previous_1_days",
        timezone: "UTC"

    });
    renderKeenMetric("#daily-active-users", "metric", dailyActiveUsersQuery, defaultHeight);

    // Daily Active Users / Total Users
    renderCalculationBetweenTwoQueries(dailyActiveUsersQuery, activeUsersQuery, "#daily-active-over-total-users", null, "percentage");


    renderKeenMetric("#monthly-active-users", "metric", monthlyActiveUsersQuery, defaultHeight, monthColor);


    // Monthly Active Users / Total Users
    renderCalculationBetweenTwoQueries(monthlyActiveUsersQuery, activeUsersQuery, "#monthly-active-over-total-users", null, 'percentage', monthColor);


    // Monthly Growth of MAU% -- Two months ago vs 1 month ago
    var twoMonthsAgoActiveUsersQuery = new keenAnalysis.Query("count_unique", {
        eventCollection: "pageviews",
        targetProperty: "user.id",
        timeframe: "previous_2_months",
        timezone: "UTC"
    });
    differenceGrowthBetweenMetrics(twoMonthsAgoActiveUsersQuery, monthlyActiveUsersQuery, activeUsersQuery, "#monthly-active-user-increase", monthColor);

    // Yearly Active Users
    var yearlyActiveUsersQuery = new keenAnalysis.Query("count_unique", {
        eventCollection: "pageviews",
        targetProperty: "user.id",
        timeframe: "previous_1_years",
        timezone: "UTC"
    });
    renderKeenMetric("#yearly-active-users", "metric", yearlyActiveUsersQuery, defaultHeight, yearColor);

    // Yearly Active Users / Total Users
    renderCalculationBetweenTwoQueries(yearlyActiveUsersQuery, activeUsersQuery, "#yearly-active-over-total-users", null, 'percentage', yearColor);

    // Average Projects per User
    renderCalculationBetweenTwoQueries(totalProjectsQuery, activeUsersQuery, "#projects-per-user", null, 'division');

    // Average Projects per MAU
    renderCalculationBetweenTwoQueries(totalProjectsQuery, monthlyActiveUsersQuery, "#projects-per-monthly-user", null, 'division');
};

// <+><+><+><+><+><+><+<+>+
//   healthy user metrics |
// ><+><+><+><+><+><+><+><+

var HealthyUserMetrics = function() {

    // stickiness ratio - DAU/MAU
    renderCalculationBetweenTwoQueries(dailyActiveUsersQuery, monthlyActiveUsersQuery, "#stickiness-ratio", null, "percentage");
};


// <+><+><+><+><+>>+
//   raw numbers   |
// ><+><+><+><><+><+

var RawNumberMetrics = function() {

    var totalDownloadsQuery = new keenAnalysis.Query("count", {
        eventCollection: "file_stats",
        timeframe: 'previous_1_days',
        filters: [{
            property_name: 'action.type',
            operator: 'eq',
            property_value: 'download_file',
            timezone: "UTC"
        }]
    });
    renderKeenMetric("#number-of-downloads", "metric", totalDownloadsQuery, defaultHeight, defaultColor, publicClient);

    var uniqueDownloadsQuery = new keenAnalysis.Query("count_unique", {
        eventCollection: "file_stats",
        timeframe: 'previous_1_days',
        target_property: 'file.resource',
        filters: [{
            property_name: 'action.type',
            operator: 'eq',
            property_value: 'download_file',
            timezone: "UTC"
        }]
    });
    renderKeenMetric("#number-of-unique-downloads", "metric", uniqueDownloadsQuery, defaultHeight, defaultColor, publicClient);

    renderKeenMetric("#total-projects", "metric", totalProjectsQuery, defaultHeight);

    var propertiesAndElements = {
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

    var piePropertiesAndElements = {
        '#total-nodes-pie': ['nodes.public', 'nodes.private'],
        '#total-projects-pie': ['projects.public', 'projects.private'],
        '#total-registered-nodes-pie': ['registered_nodes.public', 'registered_nodes.embargoed'],
        '#total-registered-projects-pie': ['registered_projects.public', 'registered_projects.embargoed']
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

    var results = {};
    Promise.all(graphPromises).then(values => {
        for (var i=0; i<values.length; i++) {
            var chart = new keenDataviz()
                .el(propertiesAndElements[values[i].query.target_property])
                .height(defaultHeight)
                .title(' ')
                .type('metric')
                .prepare();

            if (values[i].query.target_property.includes('public')) {
                chart.colors([publicColor]);
            } else if (values[i].query.target_property.includes('private') || values[i].query.target_property.includes('embargoed')) {
                chart.colors([privateColor]);
            }
            chart.data(values[i]).render();

            var targetProperty = values[i].query.target_property.toString();
            results[targetProperty] = values[i].result;
        }

        for (var element in piePropertiesAndElements) {
            if (piePropertiesAndElements.hasOwnProperty(element)) {
                var publicData = piePropertiesAndElements[element][0];
                var privateData = piePropertiesAndElements[element][1];
                c3.generate({
                    bindto: element,
                    size: {height: defaultHeight*2},
                    data: {
                        columns: [
                            ['public', results[publicData]],
                            ['private', results[privateData]],
                        ],
                        colors: {
                            public: publicColor,
                            private: privateColor
                        },
                        type : 'pie',
                    }
                });
            }
        }
    });
};

// <+><+><+><><>+
//     addons   |
// ><+><+><+<+><+

var AddonMetrics = function() {
    // Previous 7 days of linked addon by addon name
    var linked_addon = new keenAnalysis.Query("sum", {
        eventCollection: "addon_snapshot",
        targetProperty: "users.linked",
        groupBy: ["provider.name"],
        interval: "daily",
        timeframe: "previous_8_days",
        timezone: "UTC"
    });
    renderKeenMetric('#previous-7-days-of-linked-addon-by-addon-name', "line", linked_addon, defaultHeight);
};


module.exports = {
    UserGainMetrics: UserGainMetrics,
    NodeLogsPerUser: NodeLogsPerUser,
    InstitutionMetrics: InstitutionMetrics,
    ActiveUserMetrics: ActiveUserMetrics,
    HealthyUserMetrics:HealthyUserMetrics,
    RawNumberMetrics: RawNumberMetrics,
    AddonMetrics: AddonMetrics
};
