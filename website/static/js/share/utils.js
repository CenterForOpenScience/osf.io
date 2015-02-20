var m = require('mithril');


var callbacks = [];

var onSearch = function(fb) {
    callbacks.push(fb);
};

var tags = ['div', 'i', 'b', 'sup', 'p', 'span', 'sub', 'bold', 'strong', 'italic', 'a', 'small'];

var scrubHTML = function(text) {
    tags.forEach(function(tag) {
        text = text.replace(new RegExp('<' + tag + '>', 'g'), '');
        text = text.replace(new RegExp('</' + tag + '>', 'g'), '');
    });
    return text;
};

var formatNumber = function(num) {
    while (/(\d+)(\d{3})/.test(num.toString())){
        num = num.toString().replace(/(\d+)(\d{3})/, '$1'+','+'$2');
    }
    return num;
};

var loadingIcon = m('img[src=/static/img/loading.gif]',{style: {margin: 'auto', display: 'block'}});

var loadMore = function(vm) {
    if (vm.query().length === 0) {
        return;
    }
    var page = vm.page++ * 10;
    vm.resultsLoading(true);

    m.request({
        method: 'get',
        background: true,
        url: '/api/v1/share/?' + $.param({
            from: page,
            q: vm.query(),
            sort: 'dateUpdated',
        })
    }).then(function(data) {
        vm.time = data.time;
        vm.count = data.count;
        data.results.forEach(function(result) {
            result.title = scrubHTML(result.title);
            result.description = scrubHTML(result.description);
        });

        vm.results.push.apply(vm.results, data.results);

        vm.resultsLoading(false);
    }).then(m.redraw).then(function() {
        callbacks.map(function(cb) {cb();});
    });
};

var search = function(vm) {
    if (vm.query().length === 0) {
        return;
    }

    vm.page = 0;
    vm.results = [];
    // vm.showStats = false;

    loadMore(vm);
};

var appendSearch = function(vm, addendum) {
    vm.query(vm.query() + (vm.query().trim().length > 0 ? ' AND ' : '') + addendum);
    $(document.body).scrollTop(0);
    search(vm);
};

var maybeQuashEvent = function(event) {
    if (event !== undefined){
        try {
            event.preventDefault();
            event.stopPropagation();
        } catch (e) {
            window.event.cancelBubble = true;
        }
    }
};


module.exports = {
    search: search,
    onSearch: onSearch,
    loadMore: loadMore,
    loadingIcon: loadingIcon,
    formatNumber: formatNumber,
    appendSearch: appendSearch,
    maybeQuashEvent: maybeQuashEvent
};
