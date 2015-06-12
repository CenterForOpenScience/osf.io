'use strict';
var c3 = require('c3');

$(document).ready(function() {
    d3.json('/api/v1/project/a9sq6/piwikStats', function (error, data) {
    if(error){
        console.log("Error retrieving data: " + error);
    } else {
        //console.log(data);
        visualize(data);
    }
    });
});



function visualize(data){
    var visits = [];

    $.each(data, function(val) {
        console.log(data[val]);
        if(typeof data[val].nb_pageviews === 'undefined'){
            visits.push([val, 0])
        } else {
            visits.push([val, data[val].nb_pageviews]);
        }
    });

    var chart = c3.generate({
        bindto: '#piwikChart',
        data: {

        }
    })

}

