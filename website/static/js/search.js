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

    var Category = function(categoryName, categoryCount, alias){
        var self = this;
        self.name = ko.observable(categoryName.charAt(0).toUpperCase() + categoryName.slice(1));

        self.count = ko.observable(categoryCount);
        self.rawName = ko.observable(categoryName);
        self.alias = ko.observable(alias);

        self.getAlias = ko.computed(function() {
            if (self.name() === 'Total')
                return '';
            return ' AND category:' + self.alias();
        });
    };

    var ViewModel = function(url, appURL) {
        var self = this;

        self.searchStarted = ko.observable(false);
        self.queryUrl = url;
        self.appURL = appURL;
        self.category = ko.observable({});
        self.alias = ko.observable('');
        self.totalResults = ko.observable(0);
        self.resultsPerPage = ko.observable(10);
        self.currentPage = ko.observable(1);
        self.query = ko.observable('');
        self.results = ko.observableArray([]);
        self.searching = ko.observable(false);
        self.startDate = ko.observable(Date.now());
        self.endDate = ko.observable(Date('1970-01-01'));
        self.categories = ko.observableArray([]);

        self.totalCount = ko.computed(function() {
            var theCount = 0;
            $.each(self.categories(), function(index, category) {
                if(category.name() !== 'Total'){
                    theCount += category.count();
                }
            });
            return theCount;
        });

        self.totalPages = ko.computed(function() {
            if(self.totalResults() === 0){
                self.totalResults(self.totalCount());
            }
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
                    'query': self.query() + self.alias(),
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
            if(a.name() === 'Total') {
                return -1;
            } else if (b.name() === 'Total'){
                return 1;
            }
                return a.count() >  b.count() ? -1 : 1;
        };

        self.claim = function(mid) {
            claimURL = self.appURL + 'metadata/' + mid + '/promote/'
            $.osf.postJSON(claimURL, {category: 'project'}).success(function(data) {
                window.location = data.url;
            });
        };

        self.help = function() {
            bootbox.dialog({
                title: 'Search help',
                message: '<h4>Queries</h4>'+
                    '<p>Search uses the <a href="http://extensions.xwiki.org/xwiki/bin/view/Extension/Search+Application+Query+Syntax#HAND">Lucene search syntax</a>. ' +
                    'This gives you many options, but can be very simple as well. ' +
                    'Examples of valid searches include:' +
                    '<ul><li><a href="/search/?q=bird*">bird*</a></li>' +
                    '<li><a href="/search/?q=bird*+AND+source%3Ascitech">bird* AND source:scitech</a></li>' +
                    '<li><a href="/search/?q=title%3Aquantum">title:quantum</a></li></ul>' +
                    'If you want to see information from combined metadata resources rather than individual reports, try:' +
                    '<ul><li><a href="/search/?q=birds+AND+isResource%3Atrue">birds AND isResource:true</a></li></ul>' +
                    '</p>'
            });
        };

        self.filter = function(alias) {
            self.category(alias);
            self.alias(alias.getAlias());
            self.search();
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



                self.results.removeAll();

                data.results.forEach(function(result){
                    self.results.push(result);
                });


                self.categories.removeAll();
                var categories = data.counts;
                $.each(categories, function(key, value){
                    if (value === null) {
                        value = 0;
                    }
                    self.categories.push(new Category(key, value, data.typeAliases[key]));
                });
                self.categories(self.categories().sort(self.sortCategories));

                 if (self.category().name !== undefined) {
                    self.totalResults(data.counts[self.category().rawName()]);
                }
                else {
                    self.totalResults(self.totalCount());
                }

                self.categories()[0].count(self.totalCount());
                self.searchStarted(true);
                console.log(self.category().name);

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

    function Search(selector, url, appURL) {
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
