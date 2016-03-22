"use strict";

var keen = require('keen-js');
var Statistics = require('js/statistics');

keen.ready(function(){
    new Statistics();
});