var Meeting = require('../conference.js');
var Pagination = require('../emberStylePagination.js');

var ctx = window.contextVars;

new Meeting(ctx.meetingData);
new Pagination('#meetingPagination', ctx.currentPageNumber, ctx.totalPages, ctx.q, ctx.sort, ctx.hasPrevious, ctx.hasNext);
