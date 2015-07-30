var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var History = require('exports?History!history');

var callbacks = [];

var utils = {};

utils.onSearch = function(fb) {
    callbacks.push(fb);
};

var COLORBREWER_COLORS = [[166, 206, 227], [31, 120, 180], [178, 223, 138], [51, 160, 44], [251, 154, 153], [227, 26, 28], [253, 191, 111], [255, 127, 0], [202, 178, 214], [106, 61, 154], [255, 255, 153], [177, 89, 40]];
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
    vm.data = data; //TODO this is for search widgets, make for all (i.e. inc. share)
    vm.dataLoaded(true);
    m.redraw(); //TODO @bdyetton remove this, no need for readraw here if we update an m.prop (but share needs that m.prop too...)
    $.map(callbacks, function(cb) {
        cb();
    });
};

utils.loadMore = function(vm) {
    var ret = m.deferred();
    if (vm.query().length === 0) {
        ret.resolve(null);
    } else {
        var page = vm.page++ * 10;
        var sort = vm.sortMap[vm.sort()] || null;

        vm.resultsLoading(true);
        m.request({
            method: 'post',
            background: true,
            data: utils.buildQuery(vm),
            url: vm.elasticURL
        }).then(function (data) {
            vm.resultsLoading(false);
            ret.resolve(data);
        }, function (xhr, status, err) {
            ret.reject(xhr, status, err);
            utils.errorState.call(this, vm);
        });
    }
    return ret.promise;
};

utils.search = function(vm) {
    vm.dataLoaded(false);
    vm.showFooter = false;
    var ret = m.deferred();
    if (!vm.query() || vm.query().length === 0) {
        vm.query = m.prop('');
        vm.results = null;
        vm.showFooter = true;
        vm.optionalFilters = [];
        vm.requiredFilters = [];
        vm.sort('Relevance');
        History.pushState({}, 'OSF | SHARE', '?');
        ret.resolve(null);
    } else if (vm.query().length === 0) {
        ret.resolve(null);
    } else {
        vm.page = 0;
        vm.results = [];
        if (utils.stateChanged(vm)) {
            // TODO remove of range filter should update range on subgraph
            History.pushState({
                optionalFilters: vm.optionalFilters,
                requiredFilters: vm.requiredFilters,
                query: vm.query(),
                sort: vm.sort()
            }, 'OSF | SHARE', '?' + utils.buildURLParams(vm));
        }
        utils.loadMore(vm)
            .then(function (data) {
                if (vm.processStats) {
                    utils.processStats(vm, data);
                }
                utils.updateVM(vm, data);
                ret.resolve(vm);
            });
    }
    return ret.promise;
};

utils.stateChanged = function (vm) {
    var state = History.getState().data;
    return !(state.query === vm.query() && state.sort === vm.sort() &&
            utils.arrayEqual(state.optionalFilters, vm.optionalFilters) &&
            utils.arrayEqual(state.requiredFilters, vm.requiredFilters));
};

utils.buildURLParams = function(vm){
    var d = {};
    if (vm.query()) {
        d.q = vm.query();
    }
    if (vm.requiredFilters.length > 0) {
        d.required = vm.requiredFilters.join('|');
    }
    if (vm.optionalFilters.length > 0) {
        d.optional = vm.optionalFilters.join('|');
    }
    if (vm.sort()) {
        d.sort = vm.sort();
    }
    return $.param(d);
};

utils.buildQuery = function (vm) {
    var must = $.map(vm.requiredFilters, utils.parseFilter);
    var should = $.map(vm.optionalFilters, utils.parseFilter);
    var sort = {};

    if (vm.sortMap[vm.sort()]) {
        sort[vm.sortMap[vm.sort()]] = 'desc';
    }

    return {
        'query' : {
            'filtered': {
                'query': (vm.query().length > 0 && (vm.query() !== '*')) ? utils.commonQuery(vm.query()) : utils.matchAllQuery(),
                'filter': utils.boolQuery(must, null, should)
            }
        },
        'aggregations': vm.loadStats ? utils.buildStatsAggs(vm) : {},
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

utils.maybeQuashEvent = function (event) {
    if (event !== undefined) {
        try {
            event.preventDefault();
            event.stopPropagation();
        } catch (e) {
            window.event.cancelBubble = true;
        }
    }
};

utils.updateFilter = function (vm, filter, required) {
    if (required && vm.requiredFilters.indexOf(filter) === -1) {
        vm.requiredFilters.push(filter);
    } else if (vm.optionalFilters.indexOf(filter) === -1 && !required) {
        vm.optionalFilters.push(filter);
    }
    utils.search(vm);
};

utils.removeFilter = function (vm, filter) {
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

utils.arrayEqual = function (a, b) {
    return $(a).not(b).length === 0 && $(b).not(a).length === 0;
};

utils.addFiltersToQuery = function (query, filters) {
    if (filters) {
        filters.forEach(function (filter) {
            query = utils.filteredQuery(query, filter.filter);
        });
    }
    return query;
};

utils.loadRawNormalized = function(result){
    var nonJsonErrors = function(xhr) {
        return xhr.status > 200 ? JSON.stringify(xhr.responseText) : xhr.responseText;
    };
    var source = encodeURIComponent(result.shareProperties.source);
    var docID = encodeURIComponent(result.shareProperties.docID);
    return m.request({
        method: 'GET',
        url: '/api/v1/share/documents/' + source + '/' + docID + '/',
        extract: nonJsonErrors
    }).then(function(data) {

        var normed = JSON.parse(data.normalized);
        normed = JSON.stringify(normed, undefined, 2);

        var all_raw = JSON.parse(data.raw);
        result.raw = all_raw.doc;
        result.rawfiletype = all_raw.filetype;
        result.normalized = normed;
    }, function(error) {
        result.rawfiletype = 'json';
        result.normalized = '"Normalized data not found."';
        result.raw = '"Raw data not found."';
    });
};

utils.filteredQuery = function(query, filter) {
    var ret = {
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

utils.termFilter = function (field, value) {
    var ret = {'term': {}};
    ret.term[field] = value;
    return ret;
};

utils.termsFilter = function (field, value, min_doc_count) {
    min_doc_count = min_doc_count || 0;
    var ret = {'terms': {}};
    ret.terms[field] = value;
    ret.terms.size = 0;
    ret.terms.exclude = 'of|and|or';
    ret.terms.min_doc_count = min_doc_count;
    return ret;
};

utils.matchQuery = function (field, value) {
    var ret = {'match': {}};
    ret.match[field] = value;
    return ret;
};

utils.rangeFilter = function (field_name, gte, lte) {
    lte = lte || new Date().getTime();
    gte = gte || 0;
    var ret = {'range': {}};
    ret.range[field_name] = {'gte': gte, 'lte': lte};
    return ret;
};

utils.boolQuery = function (must, must_not, should, minimum) {
    var ret = {
        'bool': {
            'must': (must || []),
            'must_not': (must_not || []),
            'should': (should || [])
        }
    };
    if (minimum) {
        ret.bool.minimum_should_match = minimum;
    }

    return ret;
};

utils.dateHistogramFilter = function (field, gte, lte, interval) {
    //gte and lte in ms since epoch
    lte = lte || new Date().getTime();
    gte = gte || 0;

    interval = interval || 'week';
    return {
        'date_histogram': {
            'field': field,
            'interval': interval,
            'min_doc_count': 0,
            'extended_bounds': {
                'min': gte,
                'max': lte
            }
        }
    };
};

utils.commonQuery = function (query_string, field) {
    field = field || '_all';
    var ret = {'common': {}};
    ret.common[field] = {
        query: query_string
    };
    return ret;
};

utils.matchAllQuery = function () {
    return {
        match_all: {}
    };
};

utils.andFilter = function (filters) {
    return {
        'and': filters
    };
};

utils.queryFilter = function (query) {
    return {
        query: query
    };
};

utils.parseFilter = function (filterString) {
    // parses a filter of the form
    // filterName:fieldName:param1:param2...
    // range:providerUpdatedDateTime:2015-06-05:2015-06-16
    var parts = filterString.split(':');
    var type = parts[0];
    var field = parts[1];
    if (type === 'range') {
        return utils.rangeFilter(field, parts[2], parts[3]);
    } else if (type === 'match') {
        return utils.queryFilter(
            utils.matchQuery(field, parts[2])
        );
    }
    // Any time you add a filter, put it here
    // TODO: Maybe this would be better as a map?
};

utils.processStats = function (vm, data) {
    if (data.aggregations) {
        $.map(Object.keys(data.aggregations), function (key) { //parse data and load correctly
            if (vm.statsParsers[key]) {
                var chartData = vm.statsParsers[key](data);
                vm.statsData.charts[chartData.name] = chartData;
                if (chartData.name in vm.graphs) {
                    vm.graphs[chartData.name].load(chartData);
                }
            }
        });
    } else {
        $osf.growl('Error', 'Could not load search statistics', 'danger');
    }
};


utils.updateAggs = function (currentAgg, newAgg, global) {
    global = global || false;
    if (currentAgg) {
        if (currentAgg.all && global) {
            $.extend(currentAgg.all.aggregations, newAgg);
        } else {
            $.extend(currentAgg, newAgg);
        }
        return currentAgg;
    }

    if (global) {
        return {'all': {'global': {}, 'aggregations': newAgg}};
    }

    return newAgg;
};


utils.buildStatsAggs = function (vm) {
    var currentAggs = {};
    $.map(Object.keys(vm.aggregations), function (statQuery) {
        currentAggs = utils.updateAggs(currentAggs, vm.aggregations[statQuery]);
    });
    return currentAggs;
};

function calculateDistanceBetweenColors(color1, color2) {
    return [Math.floor((color1[0] + color2[0]) / 2),
            Math.floor((color1[1] + color2[1]) / 2),
            Math.floor((color1[2] + color2[2]) / 2)];
}

function rgbToHex(rbgIn) {
    var rgb = rbgIn[2] + (rbgIn[1] << 8) + (rbgIn[0] << 16);
    return '#' + (0x1000000 + rgb).toString(16).substring(1);
}

utils.generateColors = function (numColors) {
    var colorsToGenerate = COLORBREWER_COLORS.slice();
    var colorsUsed = [];
    var colorsOut = [];
    var colorsNorm = [];
    var color;
    while (colorsOut.length < numColors) {
        color = colorsToGenerate.shift();
        if (typeof color === 'undefined') {
            colorsToGenerate = utils.getNewColors(colorsUsed);
            colorsUsed = [];
        } else {
            colorsUsed.push(color);
            colorsNorm.push(color);
            colorsOut.push(rgbToHex(color));
        }
    }
    return colorsOut;
};

utils.getNewColors = function (colorsUsed) {
    var newColors = [];
    var i;
    for (i = 0; i < colorsUsed.length - 1; i++) {
        newColors.push(calculateDistanceBetweenColors(colorsUsed[i], colorsUsed[i + 1]));
    }
    return newColors;
};

module.exports = utils;
