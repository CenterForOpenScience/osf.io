var $ = require('jquery');
var m = require('mithril');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var History = require('exports?History!history');

var callbacks = [];

var utils = {};

utils.onSearch = function(fb) {
    callbacks.push(fb);
};

var COLORBREWER_COLORS = [[166, 206, 227], [31, 120, 180], [178, 223, 138], [51, 160, 44], [251, 154, 153], [227, 26, 28], [253, 191, 111], [255, 127, 0], [202, 178, 214], [106, 61, 154], [255, 255, 153], [177, 89, 40]];
var tags = ['div', 'i', 'b', 'sup', 'p', 'span', 'sub', 'bold', 'strong', 'italic', 'a', 'small'];

/* Removes certain HTML tags from the source */
utils.scrubHTML = function(text) {
    tags.forEach(function(tag) {
        text = text.replace(new RegExp('<' + tag + '>', 'g'), '');
        text = text.replace(new RegExp('</' + tag + '>', 'g'), '');
    });
    return text;
};

/* */
utils.formatNumber = function(num) {
    while (/(\d+)(\d{3})/.test(num.toString())){
        num = num.toString().replace(/(\d+)(\d{3})/, '$1'+','+'$2');
    }
    return num;
};

/* This resets the state of the vm on error */
utils.errorState = function(vm){
    vm.results = null;
    vm.statsData = undefined;
    vm.time = 0;
    vm.count = 0;
    vm.resultsLoading(false);
    m.redraw(true);
    $osf.growl('Error', 'invalid query');
};

/** Updates the vm with new search results
 *
 * @param {Object} vm The current state of the vm
 * @param {Object} data New search results
 */
utils.updateVM = function(vm, data) {
    if (data === null) {
        return;
    }
    vm.time = data.time;
    vm.count = data.count;
    data.results.forEach(function(result) {
        result.title = $osf.htmlDecode(result.title);
        result.description = $osf.htmlDecode(result.description || '');
    });
    vm.results.push.apply(vm.results, data.results);
    m.redraw();
    $.map(callbacks, function(cb) {
        cb();
    });
};

/* Handles searching via the search API */
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
            url: '/api/v1/share/search/'
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

/* Makes sure the state we are in is valid for searching, passes the work to loadMore if so */
utils.search = function(vm) {
    vm.showFooter = false;
    var ret = m.deferred();
    if (!vm.query() || vm.query().length === 0) {
        vm.query = m.prop('');
        vm.results = null;
        vm.showFooter = true;
        vm.showStats = false;
        vm.optionalFilters = [];
        vm.requiredFilters = [];
        vm.sort('Relevance');
        History.pushState({}, 'OSF | SHARE', '?');
        ret.resolve(null);
    } else if (vm.query().length === 0) {
        ret.resolve(null);
    } else {
        vm.showStats = true;
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
                if (vm.loadStats) {
                    if (data.aggregations) {
                        utils.processStats(vm, data);
                    } else {
                        $osf.growl('Error', 'Could not load search statistics', 'danger');
                    }
                    utils.updateVM(vm, data);
                    ret.resolve(vm);
                }
            });
    }
    return ret.promise;
};

/* Checks to see if the state of the vm has changed */
utils.stateChanged = function (vm) {
    var state = History.getState().data;
    return !(state.query === vm.query() && state.sort === vm.sort() &&
            utils.arrayEqual(state.optionalFilters, vm.optionalFilters) &&
            utils.arrayEqual(state.requiredFilters, vm.requiredFilters));
};

/* Turns the vm state into a nice-ish to look at representation that can be stored in a URL */
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

/* Builds the elasticsearch query that will be POSTed to the search API */
utils.buildQuery = function (vm) {
    var must = $.map(vm.requiredFilters, utils.parseFilter);
    var should = $.map(vm.optionalFilters, utils.parseFilter);
    var from = (vm.page - 1) * 10;
    var sort = {};
    var query = (vm.query().length > 0 && (vm.query() !== '*')) ? utils.commonQuery(vm.query()) : utils.matchAllQuery();
    var builtQuery = {};
    var filters = utils.boolQuery(must, null, should);
    if (Object.keys(filters).length === 0) {
        builtQuery = query;
    } else {
        builtQuery.filtered = {
            query: query,
            filter: filters
        };
    }

    if (vm.sortMap[vm.sort()]) {
        sort[vm.sortMap[vm.sort()]] = 'desc';
    } else {
        sort = null;
    }

    // size defaults to 10, left out intentionally
    var ret = {
        'query' : builtQuery,
        'aggregations': vm.loadStats ? utils.buildStatsAggs(vm) : {},
        'highlight': {
            'fields': {
                'title': {'fragment_size': 2000},
                'description': {'fragment_size': 2000},
                'contributors.name': {'fragment_size': 2000}
            }
        }
    };

    if (sort) {
        ret.sort = sort;
    }
    if (from !== 0) {
        ret.from = from;
    }
    return ret;
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

/* Adds a filter to the list of filters if it doesn't already exist */
utils.updateFilter = function (vm, filter, required) {
    var filters = ensureArray(filter);
    filters.forEach(function(f){
        if (required && vm.requiredFilters.indexOf(f) === -1) {
            vm.requiredFilters.push(f);
        } else if (vm.optionalFilters.indexOf(f) === -1 && !required) {
            vm.optionalFilters.push(f);
        }
    });
    utils.search(vm);
};

function ensureArray(value) {
    return Array.isArray(value) ? value : [value];
}

/* Removes a filter from the list of filters */
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

/* Tests array equality */
utils.arrayEqual = function (a, b) {
    return $(a).not(b).length === 0 && $(b).not(a).length === 0;
};

/* Loads the raw and normalized data for a specific result */
utils.loadRawNormalized = function(result){
    var source = encodeURIComponent(result.shareProperties.source);
    var docID = encodeURIComponent(result.shareProperties.docID);
    return m.request({
        method: 'GET',
        url: '/api/v1/share/documents/' + source + '/' + docID + '/',
        unwrapSuccess: function(data) {
            var unwrapped = {};
            var normed = JSON.parse(data.normalized);
            var allRaw = JSON.parse(data.raw);
            unwrapped.normalized = JSON.parse(data.normalized);
            unwrapped.raw = allRaw.doc;
            unwrapped.rawfiletype = allRaw.filetype;
            unwrapped.normalized = normed;

            return unwrapped;
        },
        unwrapError: function(response, xhr) {
            var error = {};
            error.rawfiletype = 'json';
            error.normalized = 'Normalized data not found.';
            error.raw = '"Raw data not found."';
            if (xhr.status >= 500) {
                Raven.captureMessage('SHARE Raw and Normalized API Internal Server Error.', {
                    extra: {textStatus: xhr.status}
                });
            }

            return error;
        }
    });
};

/*** Elasticsearch functions below ***/

/* Creates a filtered query */
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

/* Creates a terms filter (their names, not ours) */
utils.termsFilter = function (field, value, minDocCount) {
    minDocCount = minDocCount || 0;
    var ret = {'terms': {}};
    ret.terms[field] = value;
    ret.terms.size = 0;
    ret.terms.exclude = 'of|and|or';
    ret.terms.min_doc_count = minDocCount;
    return ret;
};

/* Creates a match query */
utils.matchQuery = function (field, value) {
    var ret = {'match': {}};
    ret.match[field] = value;
    return ret;
};

/* Creates a range filter */
utils.rangeFilter = function (fieldName, gte, lte) {
    lte = lte || new Date().getTime();
    gte = gte || 0;
    var ret = {'range': {}};
    ret.range[fieldName] = {'gte': gte, 'lte': lte};
    return ret;
};

/* Creates a bool query */
utils.boolQuery = function (must, mustNot, should, minimum) {
    var ret = {};
    var mustProvided = must && (must.length > 0);
    var mustNotProvided = mustNot && (mustNot.length > 0);
    var shouldProvided = should && (should.length > 0);

    if (!mustProvided && !mustNotProvided && !shouldProvided) {
        return ret;
    } else {
        ret.bool = {};
    }

    if (mustProvided) {
        ret.bool.must = must;
    }
    if (mustNotProvided) {
        ret.bool.must_not = mustNot;
    }
    if (shouldProvided) {
        ret.bool.should = should;
    }
    if (minimum) {
        ret.bool.minimum_should_match = minimum;
    }

    return ret;
};

/* Creates a date histogram filter */
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

/* Creates a common query */
utils.commonQuery = function (queryString, field) {
    field = field || '_all';
    var ret = {'common': {}};
    ret.common[field] = {
        query: queryString
    };
    return ret;
};

/* Creates a match_all query */
utils.matchAllQuery = function () {
    return {
        match_all: {}
    };
};

/* Creates an and filter */
utils.andFilter = function (filters) {
    return {
        'and': filters
    };
};

/* Creates a query filter */
utils.queryFilter = function (query) {
    return {
        query: query
    };
};

/**
 * Parses a filter string into one of the above filters
 *
 * parses a filter of the form
 *  filterName:fieldName:param1:param2...
 *  ex: range:providerUpdatedDateTime:2015-06-05:2015-06-16
 * @param {String} filterString A string representation of a filter dictionary
 */
utils.parseFilter = function (filterString) {
    var parts = filterString.split(':');
    var type = parts[0];
    var field = parts[1];

    // Any time you add a filter, put it here
    switch(type) {
        case 'range':
            return utils.rangeFilter(field, parts[2], parts[3]);
        case 'match':
            return utils.queryFilter(
                utils.matchQuery(field, parts[2])
            );
    }
};

utils.processStats = function (vm, data) {
    Object.keys(data.aggregations).forEach(function (key) { //parse data and load correctly
        if (vm.statsParsers[key]) {
            var chartData = vm.statsParsers[key](data);
            vm.statsData.charts[chartData.name] = chartData;
            if (chartData.name in vm.graphs) {
                vm.graphs[chartData.name].load(chartData);
            }
        }
    });
};


utils.updateAggs = function (currentAgg, newAgg, globalAgg) {
    globalAgg = globalAgg || false;

    //var returnAgg = currentAgg;
    if (currentAgg) {
        var returnAgg = $.extend({},currentAgg);
        if (returnAgg.all && globalAgg) {
            $.extend(returnAgg.all.aggregations, newAgg);
        } else {
            $.extend(returnAgg, newAgg);
        }
        return returnAgg;
    }

    if (globalAgg) {
        return {'all': {'global': {}, 'aggregations': newAgg}};
    }

    return newAgg; //else, do nothing
};


utils.buildStatsAggs = function (vm) {
    var currentAggs = {};
    $.map(Object.keys(vm.statsQueries), function (statQuery) {
        currentAggs = utils.updateAggs(currentAggs, vm.statsQueries[statQuery].aggregations);
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
    var color;
    while (colorsOut.length < numColors) {
        color = colorsToGenerate.shift();
        if (typeof color === 'undefined') {
            colorsToGenerate = utils.getNewColors(colorsUsed);
        } else {
            colorsUsed.push(color);
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
