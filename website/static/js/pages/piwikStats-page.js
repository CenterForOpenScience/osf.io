'use strict';
var c3 = require('c3');
require('c3/c3.css');

$(document).ready(function() {
    $.getJSON('/api/v1/project/a9sq6/piwikStats', function (data) {
        console.log(data);
        $('.piwikChart').height(200);
        visualize(data);
    });
});

function visualize(data){
    var visits = [];
    var dates = [];
    var highchartsdata = [];

    $.each(data, function(val, key) {
        console.log('i was called');
        dates.push(val);
        var dateNum = val.split('-');
        if(typeof key.nb_pageviews === 'undefined'){
            visits.push(0);
            highchartsdata.push([Date.UTC(+dateNum[0], +dateNum[1], +dateNum[2]), 0]);
        } else {
            visits.push(key.nb_pageviews);
            highchartsdata.push([Date.UTC(+dateNum[0], +dateNum[1], +dateNum[2]), key.nb_pageviews]);
        }
    });

    dates.unshift('x');
    visits.unshift('Pageviews');
    highchartsdata.sort(function(a, b) {
            if (a[0] === b[0]) {
                return 0;
            }
            else {
                return (a[0] < b[0]) ? -1 : 1;
            }
     });
    console.log(highchartsdata);

   $(function () {
    $('.highchart').highcharts({
        xAxis: {
            type: 'datetime',
            dateTimeLabelFormats: {
                month: '%e. %b',
                year: '%b'
            }
        },
        yAxis: {
            min: 0,
            title: {
                text: ""
            }
        },
        series: [{
            name: 'Pageviews',
            data: highchartsdata
        }],
        chart: {
            width: $('.highchart').width()

        }
    });
});

    var chart = c3.generate({
        bindto: '.piwikChart',
        data: {
            x: 'x',
            columns: [
                dates,
                visits
            ]
        },
        axis: {
            x: {
                type: 'timeseries',
                tick: {
                    format: '%b %d'
                }
            }
        },
        legend: {
            show: false
        },
        padding: {
            left: 50,
            right: 50,
            bottom: 20
        }
    });

}

