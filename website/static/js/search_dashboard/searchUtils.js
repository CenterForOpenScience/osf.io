var $ = require('jquery');
var m = require('mithril');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var History = require('exports?History!history');

var callbacks = [];

var searchUtils = {};

var tags = ['div', 'i', 'b', 'sup', 'p', 'span', 'sub', 'bold', 'strong', 'italic', 'a', 'small'];

/* This resets the state of the vm on error */
searchUtils.errorState = function(vm){
    //TODO remove queries, sorts, and non-locked filters from all requests
    m.redraw(true);
    $osf.growl('Error', 'invalid query');
};

searchUtils.runRequest = function(vm, request, data) {
    var ret = m.deferred();
    var runRequest = true;
    if (request.preRequest) {
        runRequest = request.preRequest.every(function (funcToRun) {
            var returnedRequest = funcToRun(request, data);
            if (!returnedRequest) {
                return false; //if any of the preRequest functions return false, then dont run this request
            }
            request = returnedRequest;
            return true;
        });
    }

    if (runRequest) {
        m.startComputation();
        request.complete(false);
        return m.request({
            method: 'post',
            background: true,
            data: searchUtils.buildQuery(request),
            url: '/api/v1/search/'
        }).then(function (data) {
            var oldData = request.data;
            request.data = data;
            if (oldData !== null && request.page > 0) { //Add old results back on for pagination, but what about if we want to drop all results???
                request.data.results = oldData.results.concat(request.data.results);
            }
            if (request.postRequest) {
                request.postRequest.forEach(function (funcToRun) {
                    request = funcToRun(request, data);
                });
            }
            request.complete(true);
            return data;
        }, function (xhr, status, err) {
            ret.reject(xhr, status, err);
            searchUtils.errorState.call(this, vm);
        });
    }
    return ret.promise;
};

searchUtils.runRequests = function(vm){
    if (searchUtils.hasRequestStateChanged(vm)) {
        searchUtils.pushRequestsToHistory(vm);
    }
    vm.requestOrder.forEach(function(parallelReqs){
        searchUtils.recursiveRequest(vm, parallelReqs);
    });
};

searchUtils.recursiveRequest = function(vm, requests, level, data){

    if (level === undefined){
        level = 0; //initial call
    } else {
        level = level + 1; //intermediate call
        if (level >= requests.length){
            return; //final call
        }
    }
    if (vm.requests[requests[level]]) {
        searchUtils.runRequest(vm, vm.requests[requests[level]], data).then(function(newData){
            m.endComputation();
            searchUtils.recursiveRequest(vm, requests, level, newData);
        });
    }
};

searchUtils.paginateRequests = function(vm, requests){
    if (requests.length === 0){
        for (var request in vm.requests) {
            if (vm.requests.hasOwnProperty(request)) {
                requests.push(vm.requests[request]);
            }
        }
    }

    requests.forEach(function(request) {
        if (request.page !== undefined){
            request.page = request.page + 1;
        }
    });
    searchUtils.runRequests(vm);
};

/* updates the current state when history changed. Should be bound to forward/back buttons callback */
searchUtils.updateRequestsFromHistory = function(vm){
    var state = History.getState().data.requests;
    for (var request in vm.requests) {
        if (vm.requests.hasOwnProperty(request) && state.hasOwnProperty(request)) {
            vm.requests[request].optionalFilters = state[request].optionalFilters;
            vm.requests[request].requiredFilters = state[request].requiredFilters;
            vm.requests[request].query(state[request].query);
            vm.requests[request].sort(state[request].sort);
        }
    }
    searchUtils.runRequests(vm);
};

searchUtils.pushRequestsToHistory = function(vm){
    History.pushState(
        {requests: vm.requests},
        document.getElementsByTagName("title")[0].innerHTML,
        '?' + searchUtils.buildURLParams(vm)
    );
};

/* Checks to see if the state of the vm has changed */
searchUtils.hasRequestStateChanged = function (vm) {
    for (var request in vm.requests) {
        if (vm.requests.hasOwnProperty(request)) {
            var stateChanged = searchUtils.hasRequestStateChanged(vm, vm.requests[request]);
            if (stateChanged) {
                return true;
            }
        }
    }
    return false;
};

searchUtils.hasRequestStateChanged = function (vm, currentRequest){
    var state = History.getState().data;
    if (state.requests) {
        if (state.requests.hasOwnProperty(currentRequest.id)) {
            var oldRequest = state.requests[currentRequest.id];
            var isEqual = (oldRequest.query === currentRequest.query() && oldRequest.sort === currentRequest.sort() &&
            searchUtils.arrayEqual(oldRequest.optionalFilters, currentRequest.optionalFilters) &&
            searchUtils.arrayEqual(oldRequest.requiredFilters, currentRequest.requiredFilters));
            if (isEqual) {
                return false;
            }
        }
    }
    return true;
};

/* Turns the vm state into a nice-ish to look at representation that can be stored in a URL */
searchUtils.buildURLParams = function(vm){
    var d = {};
    for (var request in vm.requests) {
        if (vm.requests.hasOwnProperty(request)) {
            d[request] = {};
            if (vm.requests[request].query()) {
                d[request].q = vm.requests[request].query();
            }
            if (vm.requests[request].requiredFilters.length > 0) {
                d[request].required = vm.requests[request].requiredFilters.join('|');
            }
            if (vm.requests[request].optionalFilters.length > 0) {
                d[request].optional = vm.requests[request].optionalFilters.join('|');
            }
            if (vm.requests[request].sort()) {
                d[request].sort = vm.requests[request].sort();
            }
        }
    }
    return $.param(d);
};

/* Builds the elasticsearch query that will be POSTed to the search API */
searchUtils.buildQuery = function (vm) {
    var must = $.map(vm.requiredFilters, searchUtils.parseFilter);
    var should = $.map(vm.optionalFilters, searchUtils.parseFilter);
    var size = vm.size || 10;
    var sort = {};

    if (vm.sortMap){
        if (vm.sortMap[vm.sort()]) {
            sort[vm.sortMap[vm.sort()]] = 'desc';
        }
    }

    return {
        'query' : {
            'filtered': {
                'query': (vm.query().length > 0 && (vm.query() !== '*')) ? searchUtils.commonQuery(vm.query()) : searchUtils.matchAllQuery(),
                'filter': searchUtils.boolQuery(must, null, should)
            }
        },
        'aggregations': searchUtils.buildAggs(vm),
        'from': vm.page * size,
        'size': size,
        'sort': [sort],
        'highlight': { //TODO work out what this does and generalize
            'fields': {
                'title': {'fragment_size': 2000},
                'description': {'fragment_size': 2000},
                'contributors.name': {'fragment_size': 2000}
            }
        }
    };

};

/* Adds a filter to the list of filters if it doesn't already exist */
searchUtils.updateFilter = function (vm, requests, filter, required) {
    if (requests.length === 0){
        for (var request in vm.requests) {
            if (vm.requests.hasOwnProperty(request)) {
                requests.push(vm.requests[request]);
            }
        }
    }

    requests.forEach(function(request) {
        if (required && request.requiredFilters.indexOf(filter) === -1) {
            request.requiredFilters.push(filter);
            request.page = 0;
        } else if (request.optionalFilters.indexOf(filter) === -1 && !required) {
            request.optionalFilters.push(filter);
            request.page = 0;
        }
    });
    searchUtils.runRequests(vm);
};

/* Removes a filter from the list of filters */
searchUtils.removeFilter = function (vm, requests, filter) {
    if (requests.length === 0){
        for (var request in vm.requests) {
            if (vm.requests.hasOwnProperty(request)) {
                requests.push(vm.requests[request]);
            }
        }
    }

    requests.forEach(function(request){
        var reqIndex = request.requiredFilters.indexOf(filter);
        var optIndex = request.optionalFilters.indexOf(filter);
        if (reqIndex > -1) {
            request.requiredFilters.splice(reqIndex, 1);
            request.page = 0; //reset the page will reset the results.
        }
        if (optIndex > -1) {
            request.optionalFilters.splice(optIndex, 1);
            request.page = 0;
        }
    });
    searchUtils.runRequests(vm);
};

/* Tests array equality */
searchUtils.arrayEqual = function (a, b) {
    return $(a).not(b).length === 0 && $(b).not(a).length === 0;
};

/**
 * Parses a filter string into one of the above filters
 *
 * parses a filter of the form
 *  filterName:fieldName:param1:param2...
 *  ex: range:providerUpdatedDateTime:2015-06-05:2015-06-16
 * @param {String} filterString A string representation of a filter dictionary
 */
searchUtils.parseFilter = function (filterString) {
    var filterParts = filterString.split('='); //remove lock qualifier if it exists
    var parts = filterParts[0].split(':');
    var type = parts[0];
    var field = parts[1];

    // Any time you add a filter, put it here
    switch(type) {
        case 'range':
            return searchUtils.rangeFilter(field, parts[2], parts[3]);
        case 'match':
            return searchUtils.queryFilter(
                searchUtils.matchQuery(field, parts[2])
            );
    }
};

searchUtils.updateAgg = function (currentAgg, newAgg, globalAgg) {
    globalAgg = globalAgg || false;

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


searchUtils.buildAggs = function (vm) {
    var currentAggs = {};
    if (vm.aggregations === undefined) {return []; }
    $.map(vm.aggregations, function (agg) {
        currentAggs = searchUtils.updateAgg(currentAggs, agg);
    });
    return currentAggs;
};

/*** Elasticsearch functions below ***/

/* Creates a filtered query */
searchUtils.filteredQuery = function(query, filter) {
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

searchUtils.termsFilter = function (field, value, minDocCount, exclustions) {
    minDocCount = minDocCount || 0;
    exclustions = ('|'+ exclustions) || '';
    var ret = {'terms': {}};
    ret.terms[field] = value;
    ret.terms.size = 0;
    ret.terms.exclude = 'of|and|or' + exclustions;
    ret.terms.min_doc_count = minDocCount;
    return ret;
};

/* Creates a match query */
searchUtils.matchQuery = function (field, value) {
    var ret = {'match': {}};
    ret.match[field] = value;
    return ret;
};

/* Creates a range filter */
searchUtils.rangeFilter = function (fieldName, gte, lte) {
    lte = lte || new Date().getTime();
    gte = gte || 0;
    var ret = {'range': {}};
    ret.range[fieldName] = {'gte': gte, 'lte': lte};
    return ret;
};

/* Creates a bool query */
searchUtils.boolQuery = function (must, mustNot, should, minimum) {
    var ret = {
        'bool': {
            'must': (must || []),
            'must_not': (mustNot || []),
            'should': (should || [])
        }
    };
    if (minimum) {
        ret.bool.minimum_should_match = minimum;
    }

    return ret;
};

/* Creates a date histogram filter */
searchUtils.dateHistogramFilter = function (field, gte, lte, interval) {
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
searchUtils.commonQuery = function (queryString, field) {
    field = field || '_all';
    var ret = {'common': {}};
    ret.common[field] = {
        query: queryString
    };
    return ret;
};

/* Creates a match_all query */
searchUtils.matchAllQuery = function () {
    return {
        match_all: {}
    };
};

/* Creates an and filter */
searchUtils.andFilter = function (filters) {
    return {
        'and': filters
    };
};

/* Creates a query filter */
searchUtils.queryFilter = function (query) {
    return {
        query: query
    };
};

module.exports = searchUtils;
