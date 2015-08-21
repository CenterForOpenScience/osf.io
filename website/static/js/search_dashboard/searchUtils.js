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
    for (var request in vm.requests) {
        if (vm.requests.hasOwnProperty(request)) {
            vm.requests[request].query = m.prop('*');
            vm.requests[request].userDefinedANDFilters = [];
            vm.requests[request].userDefinedORFilters = [];
            //vm.requests[request].sort = m.sort('*') // TODO Default sort should be saved so it can be repopulated here
        }
    }
    m.redraw(true);
    if (vm.errorHandlers.invalidQuery) { //Add other errors here
        vm.errorHandlers.invalidQuery(vm);
    }
};

/**
 * Makes request to elastic
 *
 * @param {object} vm: searchDashboard viewmodel
 * @param {object} request: objects of request parameters
 * @param {object} data: input data (possibly from previous requests) to feed into any preRequest functions
 * @return {object} a promise
 */
searchUtils.runRequest = function(vm, request, data) {
    var ret = m.deferred();
    var runRequest = true;
    if (request.preRequest) {
        runRequest = request.preRequest.every(function (funcToRun) {
            var returnedRequest = funcToRun(request, data);
            if (!returnedRequest) {
                return false; //if any of the preRequest functions return false, then don't run this request
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

/**
 * Runs all requests contained in vm according to the requestOrder specified in the view model
 *
 * @param {object} vm: searchDashboard viewmodel with requests to run
 */
searchUtils.runRequests = function(vm){
    if (searchUtils.hasRequestsStateChanged(vm)) {
        searchUtils.pushRequestsToHistory(vm);
    }
    vm.requestOrder.forEach(function(parallelReqs){ //TODO move to async.js instead of this custom parellel/serial request
        searchUtils.recursiveRequest(vm, parallelReqs);
    });
};

/**
 * Recursively and asynchronously run requests, only running the next when the previous has complete
 *
 * @param {object} vm: searchDashboard viewmodel
 * @param {object} requests: serial requests to run, one after the other
 * @param {int} level: level to handle recusive nature of function, handled internally, this can be set undefined
 * @param {object} data: data from previous request to use in new request
 */
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
            m.endComputation(); //trigger mithril to redraw, or decrement redraw counter
            searchUtils.recursiveRequest(vm, requests, level, newData);
        });
    }
};

/**
 * Get another page worth of results from specified requests
 *
 * @param {object} vm: searchDashboard view model
 * @param {array} requests: a list of requests to get more results from, note if request.page does not exist, then request will not run
 */
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

/**
 * populate requests with data from history, then run these requests, called on forward/back buttons by history.js
 *
 * @param {object} vm: searchDashboard viewmodel
 */
searchUtils.updateRequestsFromHistory = function(vm){
    var state = History.getState().data.requests;
    for (var request in vm.requests) {
        if (vm.requests.hasOwnProperty(request) && state.hasOwnProperty(request)) {
            vm.requests[request].userDefinedORFilters = state[request].userDefinedORFilters;
            vm.requests[request].userDefinedANDFilters = state[request].userDefinedANDFilters;
            vm.requests[request].query(state[request].query);
            vm.requests[request].sort(state[request].sort);
        }
    }
    searchUtils.runRequests(vm);
};

/**
 * Adds current requests to history
 *
 * @param {object} vm: searchDashboard viewmodel
 */
searchUtils.pushRequestsToHistory = function(vm){
    History.pushState(
        {requests: vm.requests},
        document.getElementsByTagName("title")[0].innerHTML,
        '?' + searchUtils.buildURLParams(vm)
    );
};

/**
 * Test if the state of all request has changed since last push to history
 *
 * @param {object} vm: searchDashboard viewmodel
 * @return {bool} Returns true if any of the requests have changed state, false otherwise
 */
searchUtils.hasRequestsStateChanged = function (vm) {
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

/**
 * Test if a single request has changed stage from the last push to history, called by hasRequestsStateChanged
 *
 * @param {object} vm: searchDashboard viewmodel
 * @param {object} currentRequest: request object to check against
 * @return {bool} Returns true if the request has changed state, false otherwise
 */
searchUtils.hasRequestStateChanged = function (vm, currentRequest){
    var state = History.getState().data;
    if (state.requests) {
        if (state.requests.hasOwnProperty(currentRequest.id)) {
            var oldRequest = state.requests[currentRequest.id];
            var isEqual = (oldRequest.query === currentRequest.query() && oldRequest.sort === currentRequest.sort() &&
            searchUtils.arrayEqual(oldRequest.userDefinedORFilters, currentRequest.userDefinedORFilters) &&
            searchUtils.arrayEqual(oldRequest.userDefinedANDFilters, currentRequest.userDefinedANDFilters));
            if (isEqual) {
                return false;
            }
        }
    }
    return true;
};

/**
 * Converts state of requests into url
 *
 * @param {object} vm: searchDashboard viewmodel
 * @return {string} url version of requests
 */
searchUtils.buildURLParams = function(vm){
    var d = {};
    for (var request in vm.requests) {
        if (vm.requests.hasOwnProperty(request)) {
            d[request] = {};
            if (vm.requests[request].query()) {
                d[request].query = vm.requests[request].query();
            }
            if (vm.requests[request].userDefinedANDFilters.length > 0) {
                d[request].ANDFilters = vm.requests[request].userDefinedANDFilters.join('|');
            }
            if (vm.requests[request].userDefinedORFilters.length > 0) {
                d[request].ORFilters = vm.requests[request].userDefinedORFilters.join('|');
            }
            if (vm.requests[request].sort()) {
                d[request].sort = vm.requests[request].sort();
            }
        }
    }
    return encodeURIComponent(JSON.stringify(d));
};

/**
 * Builds elasticsearch query to be posted from request
 *
 * @param {object} request: request to build from
 * @return {object} JSON formatted elastic request
 */
searchUtils.buildQuery = function (request) {
    var userMust = $.map(request.userDefinedANDFilters, searchUtils.parseFilter);
    var userShould = $.map(request.userDefinedORFilters, searchUtils.parseFilter);
    var must = $.map(request.dashboardDefinedANDFilters, searchUtils.parseFilter);
    var should = $.map(request.dashboardDefinedORFilters, searchUtils.parseFilter);
    must = must.concat(userMust);
    should = should.concat(userShould);

    var size = request.size || 10;
    var sort = {};

    if (request.sortMap){
        if (request.sortMap[request.sort()]) {
            sort[request.sortMap[request.sort()]] = 'desc';
        }
    }

    return {
        'query' : {
            'filtered': {
                'query': (request.query().length > 0 && (request.query() !== '*')) ? searchUtils.commonQuery(request.query()) : searchUtils.matchAllQuery(),
                'filter': searchUtils.boolQuery(must, null, should)
            }
        },
        'aggregations': searchUtils.buildAggs(request),
        'from': request.page * size,
        'size': size,
        'sort': [sort],
        'highlight': { //TODO @bdyetton->@fabianvf work out what this does and generalize...
            'fields': {
                'title': {'fragment_size': 2000},
                'description': {'fragment_size': 2000},
                'contributors.name': {'fragment_size': 2000}
            }
        }
    };

};

/**
 * Adds a filter to the list of filters for the requests specified. If no request specified then add to all requests.
 * Then run requests again.
 *
 * @param {object} vm: searchDashboard vm
 * @param {Array} requests: array of request ids to add to
 * @param {object} filter: filter to add
 * @param {required} isANDFilter: if the filter is to be ANDed or ORed
 */
searchUtils.updateFilter = function (vm, requests, filter, isANDFilter) {
    if (requests.length === 0){
        for (var request in vm.requests) {
            if (vm.requests.hasOwnProperty(request)) {
                requests.push(vm.requests[request]);
            }
        }
    }

    requests.forEach(function(request) {
        if (isANDFilter && request.userDefinedANDFilters.indexOf(filter) === -1) {
            request.userDefinedANDFilters.push(filter);
            request.page = 0;
        } else if (request.userDefinedORFilters.indexOf(filter) === -1 && !isANDFilter) {
            request.userDefinedORFilters.push(filter);
            request.page = 0;
        }
    });
    searchUtils.runRequests(vm);
};

/**
 * Removes a filter to the list of filters for the requests specified. If no request specified then add to all requests.
 * Then run requests again.
 *
 * @param {object} vm: searchDashboard vm
 * @param {Array} requests: array of request ids to add to
 * @param {object} filter: filter to remove
 */
searchUtils.removeFilter = function (vm, requests, filter) {
    if (requests.length === 0){
        for (var request in vm.requests) {
            if (vm.requests.hasOwnProperty(request)) {
                requests.push(vm.requests[request]);
            }
        }
    }

    requests.forEach(function(request){
        var reqIndex = request.userDefinedANDFilters.indexOf(filter);
        var optIndex = request.userDefinedORFilters.indexOf(filter);
        if (reqIndex > -1) {
            request.userDefinedANDFilters.splice(reqIndex, 1);
            request.page = 0; //reset the page will reset the results.
        }
        if (optIndex > -1) {
            request.userDefinedORFilters.splice(optIndex, 1);
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
    var parts = filterString.split(':');
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

/**
 * Adds aggregation to current aggregation, returns combination.
 * If global flag set, then agg becomes global of all elastic queries
 *
 * @param {object} currentAgg: agg object to add to
 * @param {object} newAgg: new agg to add
 * @param {bool} globalAgg: filter to add
 * @return {object} combined new agg
 */
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

/**
 * creates and returns aggregation from request object with list of aggregations
 *
 * @param {object} request: Request object with list of aggregations to add
 * @return {object} agg object in elasticsearch format
 */
searchUtils.buildAggs = function (request) {
    var currentAggs = {};
    if (request.aggregations === undefined) {return []; }
    $.map(request.aggregations, function (agg) {
        currentAggs = searchUtils.updateAgg(currentAggs, agg, false);
    });
    return currentAggs;
};

/*** Elasticsearch functions below ***/

/**
 * Creates a filtered query in elastic search format
 *
 * @param {object} query: query to bve filtered
 * @param {object} filter: filter object to apply to query
 * @return {object} elastic formatted filtered query
 */
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

/**
 * Creates a term filter in elastic search format
 *
 * @param {object} field: Field to filter on (generally feild)
 * @param {object} value: value to filter (must match this)
 * @param {object} minDocCount: The smallest number of results that must match before inclusion in results
 * @param {object} exclusions: Excluded terms from search (i.e. if it contains these values, then dont return result)
 * @return {object} elastic formatted filtered query
 */
searchUtils.termsFilter = function (field, value, minDocCount, exclusions) {
    minDocCount = minDocCount || 0;
    exclusions = ('|'+ exclusions) || '';
    var ret = {'terms': {}};
    ret.terms[field] = value;
    ret.terms.size = 0;
    ret.terms.exclude = 'of|and|or' + exclusions;
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
