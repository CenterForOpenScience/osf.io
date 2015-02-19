var m = require('mithril');


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
        url: '/api/v1/share/?sort=dateUpdated&from=' + page + '&q=' + vm.query(),
    }).then(function(data) {
        vm.time = data.time;
        vm.count = data.count;

        vm.results.push.apply(vm.results, data.results);

        vm.resultsLoading(false);
    }).then(m.redraw);
};

var search = function(vm) {
    if (vm.query().length === 0) {
        return;
    }

    vm.page = 0;
    vm.results = [];
    vm.showStats = false;

    loadMore(vm);
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
    loadMore: loadMore,
    loadingIcon: loadingIcon,
    maybeQuashEvent: maybeQuashEvent
};
