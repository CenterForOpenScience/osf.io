;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'knockoutpunches'], factory);
    } else {
        global.ShareSearch  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    // Enable knockout punches
    ko.punches.enableAll();
    var Result = function (data) {
        var self = this;

        self.contributors = ko.observableArray([]);
        self.dateCreated = ko.observable(data.dateCreated);
        self.dateUpdated = ko.observable(data.dateUpdated);
        self.description = ko.observable(data.description);
        self.url = ko.observable('');
        self.doi = ko.observable('');
        self.serviceID = ko.observable('');
        if(typeof data.id !== "undefined") {
            self.url(data.id.url);
            self.doi(data.id.doi);
            self.serviceID(data.id.serviceID);
        }
        self.source = ko.observable(data.source);
        self.tags = ko.observableArray(data.tags);
        self.title = ko.observable(data.title);
        self.maxContributors = ko.computed(function() {
            return self.contributors().length - 1;
        });

        data.contributors.forEach(function(contributor){
            self.contributors.push(new Contributor(contributor));
        });



    };

    var Contributor = function(data){
        var self = this;

        self.orcid = ko.observable(data.ORCID);
        self.email = ko.observable(data.email);
        self.family = ko.observable(data.family);
        self.given = ko.observable(data.given);
        self.middle = ko.observable(data.middle);
        self.prefix = ko.observable(data.prefix);
        self.suffix = ko.observable(data.suffix);

        self.fullname = ko.computed(function() {
           return self.family() + ', ' + self.given() + ' ' + self.middle();
        });
    };

    var ViewModel = function(url) {
        var self = this;

        self.searchStarted = ko.observable(false);
        self.queryUrl = url;
        self.totalResults = ko.observable(0);
        self.resultsPerPage = ko.observable(10);
        self.currentPage = ko.observable(1);
        self.query = ko.observable('');
        self.results = ko.observableArray([]);
        self.searching = ko.observable(false);
        self.startDate = ko.observable(Date.now());
        self.endDate = ko.observable(Date('1970-01-01'));

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
            return Math.max(self.resultsPerPage() * (self.currentPage()-1),0)
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
            }
        });

        self.dateFilter = ko.computed(function() {
            return {
                'range': {
                    'consumeFinished': {
                        'gte': self.startDate(),
                        'lte': self.endDate()
                    }
                }
            }
        });
        self.fullQuery = ko.computed(function() {
            return {
                'filtered': {
                    'query': self.queryObject()
//                    'filter': self.dateFilter()
                }
            }
        });

        self.submit = function() {
            self.currentPage(1);
            self.results.removeAll();
            self.search();
        };

        self.search = function() {
            self.searchStarted(true);
            var jsonData = {'query': self.fullQuery(), 'from': self.currentIndex(), 'size': self.resultsPerPage()};
            $.osf.postJSON(self.queryUrl , jsonData).success(function(data) {
                self.totalResults(data.total);
                self.results.removeAll();

                data.results.forEach(function(result){
                    self.results.push(new Result(result));
                });
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

    function ShareSearch(selector, url) {
        // Initialization code
        var self = this;
        self.viewModel = new ViewModel(url);
        element = $(selector).get();
        ko.applyBindings(self.viewModel, element[0]);
    }

    return ShareSearch

}));
