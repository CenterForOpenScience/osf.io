var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var History = require('exports?History!history');

var callbacks = [];

var utils = {};

utils.onSearch = function(fb) {
    callbacks.push(fb);
};

var tags = ['div', 'i', 'b', 'sup', 'p', 'span', 'sub', 'bold', 'strong', 'italic', 'a', 'small'];

utils.scrubHTML = function(text) {
    tags.forEach(function(tag) {
        text = text.replace(new RegExp('<' + tag + '>', 'g'), '');
        text = text.replace(new RegExp('</' + tag + '>', 'g'), '');
    });
    return text;
};

utils.formatNumber = function(num) {
    while (/(\d+)(\d{3})/.test(num.toString())){
        num = num.toString().replace(/(\d+)(\d{3})/, '$1'+','+'$2');
    }
    return num;
};

var loadingIcon = m('img[src=/static/img/loading.gif]',{style: {margin: 'auto', display: 'block'}});

utils.errorState = function(vm){
    vm.results = null;
    vm.statsData = undefined;
    vm.time = 0;
    vm.count = 0;
    vm.resultsLoading(false);
    m.redraw(true);
    $osf.growl('Error', 'invalid query');
};

utils.highlightField = function(result, field_name) {
    return utils.scrubHTML(result.highlight[field_name] ? result.highlight[field_name][0] : result[field_name] || '');
};

utils.updateVM = function(vm, data) {
    if (data === null) {
        return;
    }
    vm.time = data.time;
    vm.count = data.count;
    data.results.forEach(function(result) {
        result.title = utils.highlightField(result, 'title');
        result.description = utils.highlightField(result, 'description');
    });
    vm.results.push.apply(vm.results, data.results);
    m.redraw();
    $.map(callbacks, function(cb) {
        cb();
    });
};

utils.loadMore = function(vm) {
    var ret = m.deferred();
    if (vm.query().length === 0) {
        ret.resolve(null);
    }
    else {
        var page = vm.page++ * 10;
        var sort = vm.sortMap[vm.sort()] || null;

        vm.resultsLoading(true);
        m.request({
            method: 'post',
            background: true,
            data: utils.buildQuery(vm),
            url: '/api/v1/share/search/'
        }).then(function(data) {
            vm.resultsLoading(false);
            ret.resolve(data);
        }, function(xhr, status, err) {
            ret.reject(xhr, status, err);
            utils.errorState.call(this, vm);
        });
    }
    return ret.promise;
};

utils.search = function(vm) {
    vm.showFooter = false;
    var ret = m.deferred();
    if (!vm.query() || vm.query().length === 0){
        vm.query = m.prop('');
        vm.results = null;
        vm.showFooter = true;
        vm.optionalFilters = [];
        vm.requiredFilters = [];
        vm.sort('Relevance');
        utils.loadStats(vm);
        History.pushState({}, 'OSF | SHARE', '?');
        ret.resolve(null);
    }
    else if (vm.query().length === 0) {
        ret.resolve(null);
    }
    else {
        vm.page = 0;
        vm.results = [];
        if (utils.stateChanged(vm)){
            History.pushState({
                optionalFilters: vm.optionalFilters,
                requiredFilters: vm.requiredFilters,
                query: vm.query(),
                sort: vm.sort()
            }, 'OSF | SHARE', '?'+ utils.buildURLParams(vm));
        }
        utils.loadMore(vm)
            .then(function(data) {
                utils.updateVM(vm, data);
                ret.resolve(vm);
            });
    }
    return ret.promise;
};

utils.stateChanged = function(vm){
    var state = History.getState().data;
    return !(state.query === vm.query() && state.sort === vm.sort() &&
            utils.arrayEqual(state.optionalFilters, vm.optionalFilters) &&
            utils.arrayEqual(state.requiredFilters, vm.requiredFilters));
};

utils.buildURLParams = function(vm){
    var d = {};
    if (vm.query()){
        d.q = vm.query();
    }
    if (vm.requiredFilters.length > 0){
        d.required = vm.requiredFilters.join('|');
    }
    if (vm.optionalFilters.length > 0){
        d.optional = vm.optionalFilters.join('|');
    }
    if (vm.sort()){
        d.sort = vm.sort();
    }
    return $.param(d);
};

utils.buildQuery = function(vm) {
    var must = $.map(vm.requiredFilters, utils.parseToMatchFilter);
    var should = $.map(vm.optionalFilters, utils.parseToMatchFilter);
    var sort = {};

    if (vm.sortMap[vm.sort()]) {
        sort[vm.sortMap[vm.sort()]] = 'desc';
    }

    return {
        'query': (vm.query().length > 0 && (vm.query() !== '*')) ? utils.commonQuery(vm.query()) : utils.matchAllQuery(),
        'filter': utils.boolQuery(must, null, should),
        'aggregations': {},  // TODO
        'from': (vm.page - 1) * 10,
        'size': 10,
        'sort': [sort],
        'highlight': {
            'fields': {
                'title': {'fragment_size': 2000},
                'description': {'fragment_size': 2000},
                'contributors.name': {'fragment_size': 2000}
            }
        }
    };

};

utils.maybeQuashEvent = function(event) {
    if (event !== undefined){
        try {
            event.preventDefault();
            event.stopPropagation();
        } catch (e) {
            window.event.cancelBubble = true;
        }
    }
};

utils.updateFilter = function(vm, filter, required){
    if (required && vm.requiredFilters.indexOf(filter) === -1){
        vm.requiredFilters.push(filter);
    } else if (vm.optionalFilters.indexOf(filter) === -1 && !required){
        vm.optionalFilters.push(filter);
    }
    utils.search(vm);
};

utils.removeFilter = function(vm, filter){
    var reqIndex = vm.requiredFilters.indexOf(filter);
    var optIndex = vm.optionalFilters.indexOf(filter);
    if (reqIndex > -1) {
        vm.requiredFilters.splice(reqIndex, 1);
    }
    if (optIndex > -1) {
        vm.optionalFilters.splice(optIndex, 1);
    }
    utils.search(vm);
};

utils.arrayEqual = function(a, b) {
    return $(a).not(b).length === 0 && $(b).not(a).length === 0;
};

utils.loadStats = function(vm){
    vm.statsLoaded(false);

    return m.request({
        method: 'GET',
        url: '/api/v1/share/stats/?' + $.param({q: vm.query()}),
        background: true
    }).then(function(data) {
        vm.statsData = data;
        $.map(Object.keys(vm.graphs), function(type) {
            if(type === 'shareDonutGraph') {
                var count = data.charts.shareDonutGraph.columns.filter(function(val){return val[1] > 0;}).length;
                $('.c3-chart-arcs-title').text(count + ' Provider' + (count !== 1 ? 's' : ''));
            }
            vm.graphs[type].load(vm.statsData.charts[type]);
        }, utils.errorState.bind(this, vm));
        vm.statsLoaded(true);
    }).then(m.redraw);

};

utils.loadRawNormalized = function(result){
    var nonJsonErrors = function(xhr) {
        return xhr.status > 200 ? JSON.stringify(xhr.responseText) : xhr.responseText;
    }
    return m.request({
        method: 'GET',
        url: 'http://localhost:8000/documents/' + result.shareProperties.docID,
        // url: '/api/v1/share/documents/' + result.shareProperties.docID,  // TODO where will the postgres API live??
        extract: nonJsonErrors
    }).then(function(data) {

        var normed = JSON.parse(data.normalized);
        normed = JSON.stringify(normed, undefined, 2);

        var all_raw = JSON.parse(data.raw);
        result.raw = all_raw.doc;
        result.rawfiletype = all_raw.filetype;
        result.normalized = normed;

        console.log(typeof(result.raw));
        console.log(typeof(result.normalized));

    }, function(error) {
        result.rawfiletype = "json";
        result.normalized = '"normalized data not found."';
        result.raw = '"Raw data not found."';
    });
};


utils.filteredQuery = function(query, filter) {
    ret = {
        'filtered': {}
    };
    if (filter) {
        ret.filtered.filter = filter;
    }
    if (query) {
        ret.filtered.query = query;
    }
    return ret;
};

utils.termFilter = function(field, value) {
    ret = {'term': {}};
    ret.term[field] = value;
    return ret;
};

utils.matchQuery = function(field, value) {
    ret = {'match': {}};
    ret.match[field] = value;
    return ret;
};

utils.fieldRange = function(field_name, gte, lte) {
    ret = {'range': {}};
    ret.range[field_name] = {'gte': gte, 'lte': lte};
    return ret;
};

utils.boolQuery = function(must, must_not, should, minimum) {
    var ret = {
        'bool': {
            'must': (must || []),
            'must_not': (must_not || []),
            'should': (should || [])
        }
    };
    if (minimum) {
        ret.bool.minimum_should_match = minumum;
    }

    return ret;
};

utils.commonQuery = function(query_string, field) {
    field = field || '_all';
    ret = {'common': {}};
    ret.common[field] = {
        query: query_string
    };
    return ret;
};

utils.matchAllQuery = function() {
    return {
        match_all: {}
    };
};

utils.andFilter = function(filters) {
    return {
        'and': filters
    };
};

utils.queryFilter = function(query) {
    return {
        query: query
    };
};

utils.parseToMatchFilter = function(term) {
    items = term.split(':');
    return utils.queryFilter(
        utils.matchQuery(items[0], items[1])
    );
};

module.exports = utils;
