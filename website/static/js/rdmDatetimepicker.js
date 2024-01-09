var $ = require('jquery');
require('jquery-datetimepicker');
require('jquery-datetimepicker/jquery.datetimepicker.css');

var gt = require('js/rdmGettext');


function mount(selector) {
    $.datetimepicker.setLocale(gt.getBrowserLang());
    var opt = {
        format: 'Y-m-d H:i',
        formatTime: 'H:i',
        formatDate: 'Y-m-d',
        todayButton: true
    };
    return $(selector).datetimepicker(opt);
}

module.exports = {
    mount: mount
};
