var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var History = require('exports?History!history');

var callbacks = [];

var utils = {};

utils.onSearch = function(fb) {
    callbacks.push(fb);
};

var COLORBREWER_COLORS = [[166, 206, 227], [31, 120, 180], [178, 223, 138], [51, 160, 44], [251, 154, 153], [227, 26, 28], [253, 191, 111], [255, 127, 0], [202, 178, 214], [106, 61, 154], [255, 255, 153], [177, 89, 40]]
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
    if (utils.buildQuery(vm).length === 0) {
        ret.resolve(null);
    }
    else {
        var page = vm.page++ * 10;
        var sort = vm.sortMap[vm.sort()] || null;

        vm.resultsLoading(true);
        m.request({
            method: 'post',
            background: true,
            data: vm.buildQuery(),
            url: '/api/v1/share/search/?' + $.param({
                // from: page,
                // q: vm.buildQuery(),
                // sort: sort,
                v: 2
            })
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
    else if (utils.buildQuery(vm).length === 0) {
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

utils.buildQuery = function(vm){
    return [
        vm.query(),
        '(' + vm.optionalFilters.join(' OR ') + ')',
        '(' + vm.requiredFilters.join(' AND ') + ')'
    ].filter(function(a) {
        return a !== '()';
    }).join(' AND ');
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

utils.loadStats = function(vm) { //plug and play function to send elasticsearch agg and load in stats, and parse for chart
    if (vm.statsQuerys) {
        //For every aggregation required, perform a search
        $.map(Object.keys(vm.statsQuerys), function (statQuery) {
            vm.statsLoaded(false);
            m.request({
                method: 'POST', //TODO need to check if this is formed correctly!
                data: vm.statsQuerys[statQuery],
                url: '/api/v1/share/search/?' + $.param({v: 2}),
                background: true
            }).then(function (data) {
                vm.statsData = {'charts': {}}; //TODO @bdyetton remove charts namespace if not needed later
                if (data.aggregations) {
                    $.map(Object.keys(data.aggregations), function (key) { //parse data and load correctly
                        if (vm.statsParsers[key]) {
                            var chartData = vm.statsParsers[key](data);
                            vm.statsData.charts[chartData.name] = chartData;
                            if (chartData.name in vm.graphs) {
                                vm.graphs[chartData.name].load(chartData)
                            }
                        }
                    });
                }
                vm.statsLoaded(true);
            }).then(m.redraw, function () {
                console.log('failure to load stats')
            }); //TODO deal with this error correctly
        });
    }
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

utils.termsFilter = function(field, value, min_doc_count) {
    min_doc_count = min_doc_count || 0;
    var ret = {'terms': {}};
    ret.terms[field] = value;
    ret.terms.size = 0;
    ret.terms.exclude = 'of|and|or';
    ret.terms.min_doc_count = min_doc_count; //TODO break this out @bdyetton?
    return ret;
};

utils.matchQuery = function(field, value) {
    ret = {'match': {}};
    ret.match[field] = value;
    return ret;
};

utils.fieldRange = function(field_name, gte, lte) {
    lte = lte || new Date().getTime()
    gte = gte || 0;
    ret = {'range': {}};
    ret.range[field_name] = {'gte': gte, 'lte': lte};
    return ret;
};

utils.boolQuery = function(must, must_not, should, minimum) {
    minimum = minimum || 1;
    return {
        'bool': {
            'must': (must || []),
            'must_not': (must_not || []),
            'should': (should || []),
            'minimum_should_match': minimum
        }
    };
};

utils.dateHistogramFilter = function(feild,gte,lte,interval){
    //gte and lte in ms since epoch
    lte = lte || new Date().getTime()
    gte = gte || 0;

    interval = interval || 'week';
    return {
        'date_histogram': {
            'field': feild,
            'interval': interval,
            'min_doc_count': 0,
            'extended_bounds': {
                'min': gte,
                'max': lte
            }
        }
    }
};

utils.addAggtoQuery = function(query,agg)
{
    query['aggs'] = queryToAdd;
    return query;
};

utils.updateAggs = function(vm,aggs)
{
    vm.query.aggs[name] = agg
};

utils.commonQuery = function(query_string, field) {
    field = field || '_all';
    ret = {'common': {}};
    ret.common[field] = {
        query: query_string
    };
    return ret;
};

utils.andFilter = function(filters) {
    return {
        'and': filters
    };
};

utils.parseToTermQuery = function(term) {
    items = term.split(':');
    return utils.matchQuery(items[0], items[1]);
};


utils.generateColors = function(numColors) {
    var colorsToGenerate = COLORBREWER_COLORS.slice();
    var colorsUsed = [];
    var colorsOut = [];
    var colorsNorm = [];

    while (colorsOut.length < numColors) {
        var color = colorsToGenerate.shift();
        if (typeof color === 'undefined'){
            colorsToGenerate = utils.getNewColors(colorsUsed);
            colorsUsed = [];
        } else {
            colorsUsed.push(color);
            colorsNorm.push(color);
            colorsOut.push(rgbToHex(color))
        }
    }
    return colorsOut
};

utils.getNewColors = function(colorsUsed) {
    var newColors = [];
    for (var i=0; i < colorsUsed.length-1; i++) {
        newColors.push(calculateDistanceBetweenColors(colorsUsed[i], colorsUsed[i + 1]))
    }
    return newColors;
};

calculateDistanceBetweenColors = function(color1, color2) {
    return [Math.floor((color1[0] + color2[0]) / 2),
            Math.floor((color1[1] + color2[1]) / 2),
            Math.floor((color1[2] + color2[2]) / 2)]
};

function rgbToHex(rgb) {
        var rgb = rgb[2] + (rgb[1] << 8) + (rgb[0] << 16);
        return  '#' + (0x1000000 + rgb).toString(16).substring(1);
    }

module.exports = utils;
