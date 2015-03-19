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
    if (buildQuery(vm).length === 0) {
        return;
    }
    var page = vm.page++ * 10;
    var sort;
    if (vm.sort() === 'Date') {
        sort = 'dateUpdated';
    } else {
        sort = null;
    }
    vm.resultsLoading(true);

    m.request({
        method: 'get',
        background: true,
        url: '/api/v1/share/?' + $.param({
            from: page,
            q: buildQuery(vm),
            sort: sort
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
    if (buildQuery(vm).length === 0) {
        return;
    }

    vm.page = 0;
    vm.results = [];

    History.pushState({
        optionalFilters: vm.optionalFilters,
        requiredFilters: vm.requiredFilters,
        query: vm.query(),
        sort: vm.sort()
    }, 'OSF | SHARE', '?'+ $.param({
        'q': vm.query(),
        'required': vm.requiredFilters.join('|'),
        'optional': vm.optionalFilters.join('|'),
        'sort': vm.sort()
    }));

    loadMore(vm);
};

var buildQuery = function(vm){
    return [
        vm.query(),
        '(' + vm.optionalFilters.join(' OR ') + ')',
        '(' + vm.requiredFilters.join(' AND ') + ')'
    ].filter(function(a) {
        if (a === '()'){
            return false;
        }
        return true;
    }).join(' AND ');
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

var updateFilter = function(vm, filter, required){
    required = required || false;
    if (required === true && vm.requiredFilters.indexOf(filter) === -1){
        vm.requiredFilters.push(filter);
    } else if (vm.optionalFilters.indexOf(filter) === -1){
        vm.optionalFilters.push(filter);
    }
    search(vm);
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
    search(vm);
};


module.exports = {
    search: search,
    onSearch: onSearch,
    loadMore: loadMore,
    loadingIcon: loadingIcon,
    formatNumber: formatNumber,
    maybeQuashEvent: maybeQuashEvent,
    buildQuery: buildQuery,
    updateFilter: updateFilter,
    removeFilter: removeFilter
};
