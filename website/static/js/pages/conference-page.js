var Meeting = require('../conference.js');
require('../../vendor/bower_components/slickgrid/slick.core.js');
require('../../vendor/bower_components/slickgrid/slick.dataview.js');

new Meeting(window.contextVars.meetingData);
