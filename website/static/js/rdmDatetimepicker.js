var $ = require('jquery');
var moment = require('moment');
require('jquery-datetimepicker');
require('jquery-datetimepicker/jquery.datetimepicker.css');
require('jquery-mousewheel')($);

var gt = require('js/rdmGettext');


function mount(selector) {
    $.datetimepicker.setLocale(gt.getBrowserLang());
    $.datetimepicker.setDateFormatter({
        parseDate: function (date, format) {
            var d = moment(date, format, true);
            return d.isValid() ? d.toDate() : false;
        },
        formatDate: function (date, format) {
            return moment(date).format(format);
        }
    });
    var opt = {
        format: 'YYYY-MM-DD HH:mm',
        formatTime: 'HH:mm',
        formatDate: 'YYYY-MM-DD',
        closeOnTimeSelect: false,
        closeOnWithoutClick: false,
        parentID: selector,
        insideParent: true,
        todayButton: true,
        step: 1
    };
    return $(selector).datetimepicker(opt);
}

module.exports = {
    mount: mount
};
