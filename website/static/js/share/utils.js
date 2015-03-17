var m = require('mithril');
var History = require('exports?History!history');

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

    History.pushState({query: vm.query()}, 'OSF | SHARE', '?q=' + vm.query());

    loadMore(vm);
};

var buildQuery = function(vm){
    filterString = vm.optionalFilters.join([separator=' OR ']) + ' AND ' + vm.requiredFilters.join([separator=' AND ']);
    filterString = filterString.replace(/(^\s*AND\s+)|(\s+AND\s*$)|(^\s*OR\s+)|(\s+OR\s*$)/g, '');
    vm.query(filterString);
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

var addFilter = function(vm, filter, required){
    required = required || false;
    console.log(filter);
    if (required === true && vm.requiredFilters.indexOf(filter) === -1){
        vm.requiredFilters.push(filter);
    } else if (vm.optionalFilters.indexOf(filter) === -1){
        vm.optionalFilters.push(filter);
    }
    buildQuery(vm);
};

var removeFilter = function(vm, filter){
    var reqIndex = vm.requiredFilters.indexOf(filter);
    var optIndex = vm.optionalFilters.indexOf(filter);
    if (reqIndex > -1) {
        vm.requiredFilters.splice(reqIndex, 1);
    }
    if (optIndex > -1) {
        vm.optionalFilters.splice(optIndex, 1);
    }
    buildQuery(vm);
};


module.exports = {
    search: search,
    onSearch: onSearch,
    loadMore: loadMore,
    loadingIcon: loadingIcon,
    formatNumber: formatNumber,
    maybeQuashEvent: maybeQuashEvent,
    buildQuery: buildQuery,
    addFilter: addFilter,
    removeFilter: removeFilter
};
