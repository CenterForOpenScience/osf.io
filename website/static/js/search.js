;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'knockoutpunches'], factory);
    } else {
        global.Search  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    // Enable knockout punches
    ko.punches.enableAll();

    //https://stackoverflow.com/questions/7731778/jquery-get-query-string-parameters
    function qs(key) {
        key = key.replace(/[*+?^$.\[\]{}()|\\\/]/g, "\\$&"); // escape RegEx meta chars
        var match = location.search.match(new RegExp("[?&]"+key+"=([^&]+)(&|$)"));
        return match && decodeURIComponent(match[1].replace(/\+/g, " "));
    }

    var Category = function(categoryName, categroryCount){
        var self = this;
        self.name = ko.observable(categoryName.toUpperCase());
        self.count = ko.observable(categroryCount);
    };

    var ViewModel = function(url, appURL) {
        var self = this;

        self.searchStarted = ko.observable(false);
        self.queryUrl = url;
        self.appURL = appURL
        self.totalResults = ko.observable(0);
        self.resultsPerPage = ko.observable(10);
        self.currentPage = ko.observable(1);
        self.query = ko.observable('');
        self.results = ko.observableArray([]);
        self.searching = ko.observable(false);
        self.startDate = ko.observable(Date.now());
        self.endDate = ko.observable(Date('1970-01-01'));
        self.categories = ko.observableArray([]);

        self.totalPages = ko.computed(function() {
            var pageCount = 1;
            var resultsCount = Math.max(self.resultsPerPage(),1); // No Divide by Zero
            pageCount = Math.ceil(self.totalResults() / resultsCount);
            return pageCount;
        });

        self.nextPageExists = ko.computed(function() {
            return ((self.totalPages() > 1) && (self.currentPage() < self.totalPages()));
        });

        self.prevPageExists = ko.computed(function() {
            return self.totalPages() > 1 && self.currentPage() > 1;
        });

        self.currentIndex = ko.computed(function() {
            return Math.max(self.resultsPerPage() * (self.currentPage()-1),0);
        });

        self.navLocation = ko.computed(function() {
            return 'Page ' + self.currentPage() + ' of ' + self.totalPages();
        });

        self.queryObject = ko.computed(function(){
            return {
                'query_string': {
                    'default_field': '_all',
                    'query': self.query(),
                    'analyze_wildcard': true,
                    'lenient': true
                }
            };
        });

        self.dateFilter = ko.computed(function() {
            return {
                'range': {
                    'consumeFinished': {
                        'gte': self.startDate(),
                        'lte': self.endDate()
                    }
                }
            };
        });
        self.fullQuery = ko.computed(function() {
            return {
                'filtered': {
                    'query': self.queryObject()
//                    'filter': self.dateFilter()
                }
            };
        });

        self.sortCategories = function(a, b) {
                return a.count() >  b.count() ? -1 : 1;
        };

        self.claim = function(mid) {
            claimURL = self.appURL + 'metadata/' + mid + '/promote'
            $.osf.postJSON(claimURL, {}).success(function(data) {
                window.location = data.url;
            });
        };

        self.submit = function() {
            self.searchStarted(false);
            self.totalResults(0);
            self.currentPage(1);
            self.results.removeAll();
            self.search();
        };

        self.search = function() {

            var jsonData = {'query': self.fullQuery(), 'from': self.currentIndex(), 'size': self.resultsPerPage()};
            $.osf.postJSON(self.queryUrl , jsonData).success(function(data) {

                self.totalResults(data.counts.total);
                self.results.removeAll();

                data.results.forEach(function(result){
                    self.results.push(result);
                });


                self.categories.removeAll();
                var categories = data.counts;
                for (var key in categories) {
                    self.categories.push(new Category(key, categories[key]));
                }
                self.categories(self.categories().sort(self.sortCategories));
                self.searchStarted(true);

            }).fail(function(){
                console.log("error");
                self.totalResults(0);
                self.currentPage(0);
                self.results.removeAll();
            });
        };

        self.pageNext = function() {
            self.currentPage(self.currentPage() + 1);
            self.search();
        };

        self.pagePrev = function() {
            self.currentPage(self.currentPage() - 1);
            self.search();
        };

    };

    function Search(selector, url, app_url) {
        // Initialization code
        var self = this;
        var query = qs('q');
        self.viewModel = new ViewModel(url, appURL);
        if (query !== null) {
            self.viewModel.query(query);
            self.viewModel.search();
        }
        element = $(selector).get();
        ko.applyBindings(self.viewModel, element[0]);
    }

    return Search;

}));
