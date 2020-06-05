'use strict';

var ko = require('knockout');
var $ = require('jquery');
var bootbox = require('bootbox');
require('bootstrap.growl');
var History = require('exports-loader?History!history');

var siteLicenses = require('js/licenses');
var licenses = siteLicenses.list;
var DEFAULT_LICENSE = siteLicenses.DEFAULT_LICENSE;

var $osf = require('js/osfHelpers');

var rdmGettext = require('js/rdmGettext');
var gt = rdmGettext.rdmGettext();
var _ = function(msgid) { return gt.gettext(msgid); };
var agh = require('agh.sprintf');

// Disable IE Caching of JSON
$.ajaxSetup({ cache: false });

var eqInsensitive = function(str1, str2) {
    return str1.toUpperCase() === str2.toUpperCase();
};

var Category = function(name, count, display){
    var self = this;

    self.name = name;
    self.count = count;
    self.display = display;

    self.url = ko.computed(function() {
        if (self.name === 'total') {
            return '';
        }
        return self.name + '/';
    });
};

var Tag = function(tagInfo){
    var self = this;
    self.name = tagInfo.key;
    self.count = tagInfo.doc_count;
};

var License = function(name, id, count) {

    this.name = name;
    this.id = id;
    this.count = ko.observable(count);

    this.active = ko.observable(false);
};
License.prototype.toggleActive = function() {
    this.active(!this.active());
};

var User = function(result){
    var self = this;
    self.category = result.category;
    self.profileImageUrl = ko.observable('');
    self.social = result.social;
    self.job_title = result.job_title;
    self.job = result.job;
    self.degree = result.degree;
    self.school = result.school;
    self.url = result.url;
    self.user = result.user;
    self.id = result.id;
    self.comment = result.comment;
    self.highlight = result.highlight;
    self.ongoing_job = result.ongoing_job;
    self.ongoing_job_department = result.ongoing_job_department;
    self.ongoing_job_title = result.ongoing_job_title;
    self.ongoing_school = result.ongoing_school;
    self.ongoing_school_department = result.ongoing_school_department;
    self.ongoing_school_degree = result.ongoing_school_degree;

    $.ajax('/api/v1'+ result.url).done(function(data){
        if (typeof data.profile !== 'undefined') {
            self.profileImageUrl(data.profile.profile_image_url);
        }
    });
};

var isValidSort = function (sort_name, filter_name) {
    switch(sort_name) {
    case 'project_asc':
    case 'project_desc':
        switch (filter_name) {
        case 'project':
        case 'file':
        case 'wiki':
        case 'total':
            return true;

        default:
            return false;
        }
        break;

    case 'file_asc':
    case 'file_desc':
        if (filter_name === 'file' || filter_name === 'total') {
            return true;
        } else {
            return false;
        }
        break;

    case 'user_asc':
    case 'user_desc':
        if (filter_name === 'user' || filter_name === 'total') {
            return true;
        } else {
            return false;
        }
        break;

    case 'institution_asc':
    case 'institution_desc':
        if (filter_name === 'institution' || filter_name === 'total') {
            return true;
        } else {
            return false;
        }
        break;

    case 'wiki_asc':
    case 'wiki_desc':
        if (filter_name === 'wiki' || filter_name === 'total') {
            return true;
        } else {
            return false;
        }
        break;

    default:
        return true;
    }

    return false;
};

var SortOrderSettings = function(category_name) {
    var settings = [];
    var allSettings = [
        {text: _('Date Modified (Desc)'), value: 'modified_desc', enable: ko.observable(true)},
        {text: _('Date Modified (Asc)'), value: 'modified_asc', enable: ko.observable(true)},
        {text: _('Date Created (Desc)'), value: 'created_desc', enable: ko.observable(true)},
        {text: _('Date Created (Asc)'), value: 'created_asc', enable: ko.observable(true)},
        {text: _('Project name (Asc)'), value: 'project_asc', enable: ko.observable(true)},
        {text: _('Project name (Desc)'), value: 'project_desc', enable: ko.observable(true)},
        {text: _('File name (Asc)'), value: 'file_asc', enable: ko.observable(true)},
        {text: _('File name (Desc)'), value: 'file_desc', enable: ko.observable(true)},
        {text: _('User name (Asc)'), value: 'user_asc', enable: ko.observable(true)},
        {text: _('User name (Desc)'), value: 'user_desc', enable: ko.observable(true)},
        {text: _('Institution name (Asc)'), value: 'institution_asc', enable: ko.observable(true)},
        {text: _('Institution name (Desc)'), value: 'institution_desc', enable: ko.observable(true)},
        {text: _('Wiki title (Asc)'), value: 'wiki_asc', enable: ko.observable(true)},
        {text: _('Wiki title (Desc)'), value: 'wiki_desc', enable: ko.observable(true)}
    ];

    for (var i = 0, len = allSettings.length; i < len; i++) {
        if (isValidSort(allSettings[i].value, category_name) === true) {
            settings.push(allSettings[i]);
        }
    }

    return settings;
};

var ViewModel = function(params) {
    var self = this;
    self.params = params || {};
    self.queryUrl = self.params.url;
    self.appURL = self.params.appURL;

    self.tag = ko.observable('');
    self.stateJustPushed = true;
    self.query = ko.observable('');
    self.category = ko.observable({});
    self.tags = ko.observableArray([]);
    self.tagMaxCount = ko.observable(1);
    self.currentPage = ko.observable(1);
    self.totalResults = ko.observable(0);
    self.results = ko.observableArray([]);
    self.urlLists = ko.observableArray([]);
    self.searching = ko.observable(false);
    self.categories = ko.observableArray([]);
    self.shareCategory = ko.observable('');
    self.searchStarted = ko.observable(false);
    self.showSearch = true;
    self.showClose = false;
    self.searchCSS = ko.observable('active');
    self.onSearchPage = true;
    if (window.contextVars.searchSort !== null) {
        self.sortOrder = ko.observable(window.contextVars.searchSort);
    } else {
        self.sortOrder = ko.observable('modified_desc');
    }
    self.syncSortOrder = true;
    self.sortOrderSettings = ko.observableArray(SortOrderSettings('total'));
    self.pagesShown = ko.observable(10);
    self.center = Math.floor(self.pagesShown() / 2) + 1;
    self.syncResultsPerPage = true;
    self.resultsPerPageSettings = ko.observableArray([
        {text: '10', value: 10},
        {text: '20', value: 20},
        {text: '50', value: 50},
        {text: '100', value: 100}
    ]);
    if (window.contextVars.searchSize !== null) {
        self.resultsPerPage = ko.observable(Number(window.contextVars.searchSize));
    } else {
        self.resultsPerPage = ko.observable(10);
    }
    self.titleLengthLimit = 30;
    self.nameLengthLimit = 30;
    self.usernameLnegthLimit = 30;
    self.textLengthLimit = 124;
    self.commentLengthLimit = 124;

    self.licenses = ko.observable(
        $.map(licenses, function(license) {
            var l = new License(license.name, license.id, 0);
            l.active.subscribe(function() {
                self.currentPage(1);
                self.search();
            });
            return l;
        })
    );
    self.licenseNames = ko.computed(function() {
        var sortedLicenses = self.licenses() || [];
        sortedLicenses.sort(function(a, b) {
            if (a.count() > b.count()) {
                return -1;
            }
            else if (b.count() > a.count()) {
                return 1;
            }
            else {
                if (a.name > b.name) {
                    return 1;
                }
                else {
                    return -1;
                }
                return 0;
            }
        });
        return $.map(sortedLicenses, function(count, name) {
            return name;
        });
    });
    self.selectedLicenses = ko.pureComputed(function() {
        return (self.licenses() || []).filter(function(license) {
            return license.active();
        });
    });
    self.showLicenses = ko.computed(function() {
        return ['project', 'registration', 'component'].indexOf(self.category().name) >= 0;
    });
    self.category.subscribe(function(value) {
        if (['project', 'registration', 'component'].indexOf(value) < 0) {
            $.each(self.licenses(), function(i, license) {
                license.active(false);
            });
        }
    });

    // Maintain compatibility with hiding search bar elsewhere on the site
    self.toggleSearch = function() {
    };

    self.allCategories = ko.pureComputed(function(){
        if(self.shareCategory()){
            return self.categories().concat(self.shareCategory());
        }
        return self.categories();
    });

    self.totalCount = ko.pureComputed(function() {
        if (self.categories().length === 0 || self.categories()[0] === undefined) {
            return 0;
        }

        return self.categories()[0].count;
    });

    self.totalPages = ko.pureComputed(function() {
        var resultsCount = Math.max(self.resultsPerPage(), 1); // No Divide by Zero
        var countOfPages = Math.ceil(self.totalResults() / resultsCount);
        return countOfPages;
    });

    self.nextPageExists = ko.pureComputed(function() {
        return ((self.totalPages() > 1) && (self.currentPage() < self.totalPages()));
    });

    self.prevPageExists = ko.pureComputed(function() {
        return self.totalPages() > 1 && self.currentPage() > 1;
    });

    self.currentIndex = ko.pureComputed(function() {
        return Math.max(self.resultsPerPage() * (self.currentPage()-1),0);
    });

    self.navLocation = ko.pureComputed(function() {
        return agh.sprintf(_('Page %1$s of %2$s') ,self.currentPage(),self.totalPages());
    });

    self.queryObject = ko.pureComputed(function(){
        var TITLE_BOOST = '4';
        var DESCRIPTION_BOOST = '1.2';
        var JOB_SCHOOL_BOOST = '1';
        var ALL_JOB_SCHOOL_BOOST = '0.125';

        var fields = [
            '_all',
            'title^' + TITLE_BOOST,
            'description^' + DESCRIPTION_BOOST,
            'job^' + JOB_SCHOOL_BOOST,
            'school^' + JOB_SCHOOL_BOOST,
            'all_jobs^' + ALL_JOB_SCHOOL_BOOST,
            'all_schools^' + ALL_JOB_SCHOOL_BOOST
        ];
        return {
            'query_string': {
                'default_field': '_all',
                'fields': fields,
                'query': self.query(),
                'analyze_wildcard': true,
                'lenient': true
            }
        };
    });

    self.filters = function(){
        var selectedLicenses = self.selectedLicenses();
        if (selectedLicenses.length) {
            var filters = {
                terms: {
                    'license.id': $.map(selectedLicenses, function(l) {
                        return l.id;
                    })
                }
            };
            if (selectedLicenses.filter(function(l) {
                return eqInsensitive(l.id, DEFAULT_LICENSE.id);
            }).length) {
                filters = {
                    or: [
                        filters,
                        {
                            missing: {field: 'license'}
                        }
                    ]
                };
            }
            return filters;
        }
        return null;
    };

    self.fullQuery = function(filters) {
        var query = {
            filtered: {
                query: self.queryObject()
            }
        };
        if (filters) {
            query.filtered.filter = filters;
        }

        return query;
    };

    self.sortCategories = function(a, b) {
        if(a.name === 'total') {
            return -1;
        } else if (b.name === 'total') {
            return 1;
        }
        return a.count >  b.count ? -1 : 1;
    };

    self.help = function() {
        bootbox.dialog({
            title: _('Search help'),
            message: _('<h4>Queries</h4>')+
                _('<p>Search uses the <a href="http://extensions.xwiki.org/xwiki/bin/view/Extension/Search+Application+Query+Syntax">Lucene search syntax</a>. ') +
                _('This gives you many options, but can be very simple as well. ') +
                _('Examples of valid searches include:') +
                '<ul><li><a href="/search/?q=repro*">repro*</a></li>' +
                '<li><a href="/search/?q=brian+AND+title%3Amany">brian AND title:many</a></li>' +
                '<li><a href="/search/?q=tags%3A%28psychology%29">tags:(psychology)</a></li></ul>' +
                '</p>'
        });
    };

    self.filter = function(alias) {
        self.searchStarted(false);
        self.currentPage(1);
        self.category(alias);
        self.setSortOrderSettings(self.category().name);
        if (isValidSort(self.sortOrder(), self.category().name) === false) {
            self.setSortOrder('modified_desc');
        }

        var win = null;
        if (alias.name === 'SHARE') {
            win = window.open(window.contextVars.shareUrl + 'discover?' + $.param({q: self.query()}), '_blank');
            win.opener = null;
            win.focus();
        } else if (alias.name === 'preprint') {
            win = window.open(window.location.origin + '/preprints/discover?' + $.param({q: self.query()}), '_blank');
            win.opener = null;
            win.focus();
        } else {
            self.search();
        }
    };

    self._makeTagString = function(tagName) {
        return 'tags:("' + tagName.replace(/"/g, '\\\"') + '")';
    };
    self.addTag = function(tagName) {
        var tagString = self._makeTagString(tagName);
        var query = self.query();
        if (query.indexOf(tagString) === -1) {
            if (self.query() !== '') {
                query += ' AND ';
            }
            query += tagString;
            self.query(query);
            self.onUpdateTags();
        }
    };
    self.removeTag = function(tagName, _, e) {
        e.stopPropagation();
        var query = self.query();
        var tagRegExp = /(?:AND)?\s*tags\:\([\'\"](.+?)[\'\"]\)/g;
        var dirty = false;
        var match;
        while ((match = tagRegExp.exec(query))) {
            var block = match.shift();
            var tag = match.shift().trim();
            if (tag === tagName) {
                query = query.replace(block, '').trim();
                dirty = true;
            }
        }
        if (dirty) {
            self.query(query);
            self.onUpdateTags();
        }
    };
    self.onUpdateTags = function() {
        self.category(new Category('total', 0, 'Total'));
        self.currentPage(1);
        self.search();
    };

    self.submit = function() {
        $('#searchPageFullBar').blur().focus();
        self.searchStarted(false);
        self.totalResults(0);
        self.currentPage(1);
        self.setSortOrderSettings(self.category().name);
        self.search();
    };

    self.search = function(noPush, validate) {

        self.searching(true);

        // Check for NOTs and ANDs put spaces before the ones that don't have spaces
        var query = self.query().replace(/\s?NOT tags:/g, ' NOT tags:');
        query = query.replace(/\s?AND tags:/g, ' AND tags:');
        self.query(query);

        var jsonData = {
            query: self.fullQuery(self.filters()),
            from: self.currentIndex(),
            size: self.resultsPerPage()
        };
        if (window.contextVars.enablePrivateSearch) {
            jsonData = {
                'api_version': {
                    'vendor': 'grdm',
                    'version': 2
                },
                'sort': self.sortOrder(),
                'highlight': self.getHighlightLimit(),
                'elasticsearch_dsl': jsonData
            };
        }
        var url = self.queryUrl + self.category().url();

        var shareQuery = {
            query: {
                query_string: {
                    query: self.query()
                }
            }
        };

        $osf.postJSON(url, jsonData).done(function(data) {

            //Clear out our variables
            self.tags([]);
            self.tagMaxCount(1);
            self.results.removeAll();
            self.urlLists.removeAll();
            self.categories.removeAll();
            self.shareCategory('');

            // Deep copy license list
            var licenseCounts = self.licenses().slice();
            var noneLicense;
            for(var i = 0; i < licenseCounts.length; i++) {
                var l = licenseCounts[i];
                l.count(0);
                if (eqInsensitive(l.id, DEFAULT_LICENSE.id)) {
                    noneLicense = l;
                }
            }
            noneLicense.count(0);
            var nullLicenseCount = data.aggs.total || 0;
            if ((data.aggs || {}).licenses)  {
                $.each(data.aggs.licenses, function(key, value) {
                    var licenseCount = licenseCounts.filter(function(l) {
                        return eqInsensitive(l.id, key);
                    })[0];
                    if (licenseCount) {
                        licenseCount.count(value);
                    }
                    nullLicenseCount -= value;
                });
            }
            noneLicense.count(noneLicense.count() + nullLicenseCount);
            self.licenses(licenseCounts);

            data.results.forEach(function(result){
                if (result.category === 'user') {
                    if ($.inArray(result.url, self.urlLists()) === -1) {
                        self.results.push(new User(result));
                        self.urlLists.push(result.url);
                    }
                }
                else {
                    if (typeof result.url !== 'undefined') {
                        result.wikiUrl = result.url+'wiki/';
                        result.filesUrl = result.url+'files/';
                    }
                    self.results.push(result);
                }
                if (result.category === 'registration') {
                    result.dateRegistered = new $osf.FormattableDate(result.date_registered);
                } else if (result.category === 'preprint') {
                    result.preprintUrl = result.preprint_url;
                }
            });

            //Load our categories
            var categories = data.counts;
            $.each(categories, function(key, value){
                if (value === null) {
                    value = 0;
                }
                self.categories.push(new Category(key, value, _(data.typeAliases[key])));
            });

            self.categories(self.categories().sort(self.sortCategories));

            // If our category is named attempt to load its total else set it to the total total
            var selectedLicenses = self.selectedLicenses();
            if (self.category().name !== undefined) {
                if (selectedLicenses.length) {
                    var total = 0;
                    $.each(selectedLicenses, function(i, license) {
                        total += license.count();
                    });
                    self.totalResults(total);
                }
                else {
                    self.totalResults(data.counts[self.category().name] || 0);
                }
            } else {
                self.totalResults(self.self.categories()[0].count);
            }

            // Load up our tags
            $.each(data.tags, function(key, value){
                self.tags.push(new Tag(value));
                self.tagMaxCount(Math.max(self.tagMaxCount(), value.doc_count));
            });

            self.searchStarted(true);

            if (validate) {
                self.validateSearch();
            }

            if (!noPush) {
                self.pushState();
            }

            $osf.postJSON(window.contextVars.shareUrl + 'api/v2/search/creativeworks/_count', shareQuery).done(function(data) {
                if(data.count > 0) {
                    self.shareCategory(new Category('SHARE', data.count, 'SHARE'));
                }
            });

            self.searching(false);

        }).fail(function(response){
            self.totalResults(0);
            self.currentPage(0);
            self.results([]);
            self.tags([]);
            self.categories([]);
            self.searchStarted(false);
            self.searching(false);
            $osf.handleJSONError(response);
        });

    };

    self.paginate = function(val) {
        window.scrollTo(0, 0);
        self.currentPage(self.currentPage() + val);
        self.search();
    };

    self.pagePrev = self.paginate.bind(self, -1);
    self.pageNext = self.paginate.bind(self, 1);

    self.pageNth = function(val) {
        window.scrollTo(0, 0);
        self.currentPage(val);
        self.search();
    };

    self.pageFirst = function() {
        self.pageNth(1);
    };

    self.pageLast = function() {
        self.pageNth(self.totalPages());
    };

    self.pageNthByUser = function() {
        window.scrollTo(0, 0);
        self.search();
    };

    self.listIndices = function() {
        var pages = [];
        var i;
        if (self.totalPages() < self.pagesShown()) {
            for (i = 1; i <= self.totalPages(); i++) {
                pages.push(i);
            }
            return pages;
        }

        if (self.currentPage() <= self.center) {
            for (i = 1; i <= self.pagesShown(); i++) {
                pages.push(i);
            }
            return pages;
        }

        var linksBeforeCurrent = Math.ceil((self.pagesShown() - 2) / 2);
        var linksAfterCurrent = Math.floor((self.pagesShown() - 2) / 2) + 1;
        if ((self.currentPage() + linksAfterCurrent + 1) < self.totalPages()) {
            for (i = self.currentPage() - linksBeforeCurrent; i <= self.currentPage() + linksAfterCurrent; i++) {
                pages.push(i);
            }
            return pages;
        }

        for (i = self.totalPages() - (self.pagesShown() - 1); i <= self.totalPages(); i++) {
            pages.push(i);
        }
        return pages;
    };

    //History JS callback
    self.pageChange = function() {
        if (self.stateJustPushed) {
            self.stateJustPushed = false;
            return;
        }

        self.loadState();

        self.search(true);
    };

    //Ensure that the first url displays properly
    self.validateSearch = function() {
        var possibleCategories;
        if (self.category().name !== undefined) {
            possibleCategories = $.map(self.categories().filter(function(category) {
                return category.count > 0;
            }), function(category) {
                return category.name;
            });

            if (possibleCategories.indexOf(self.category().name) === -1 && possibleCategories.length !== 0) {
                self.filter(self.categories()[0]);
                return self.search(true);
            }
        }
        if (self.currentPage() > self.totalPages() && self.currentPage() !== 1) {
            self.currentPage(self.totalPages());
            return self.search(true);
        }
    };

    //Load state from History JS
    self.loadState = function() {
        var state = History.getState().data;
        self.currentPage(state.page || 1);
        self.setCategory(state.filter);
        self.setResultsPerPage(state.size || (window.contextVars.searchSize || 10));
        self.setSortOrderSettings(self.category().name);
        self.setSortOrder(state.sort || window.contextVars.searchSort);
        self.query(state.query || '');
    };

    //Push a new state to History
    self.pushState = function() {
        var state = {
            filter: '',
            query: self.query(),
            sort: self.sortOrder(),
            size: self.resultsPerPage(),
            page: self.currentPage(),
            scrollTop: $(window).scrollTop()
        };

        var url = '?q=' + self.query();

        if (self.category().name !== undefined && self.category().url() !== '') {
            state.filter = self.category().name;
            url += ('&filter=' + self.category().name);
        }

        if (self.sortOrder() !== undefined) {
            url += ('&sort=' + self.sortOrder());
        }

        if (self.resultsPerPage() !== undefined) {
            url += ('&size=' + self.resultsPerPage());
        }

        url += ('&page=' + self.currentPage());

        //Indicate that we've just pushed a state so the
        //Call back does not process this push as a state change
        self.stateJustPushed = true;
        History.pushState(state, _('GakuNin RDM | Search'), url);
    };

    self.setCategory = function(cat) {
        if (cat !== undefined && cat !== null && cat !== '') {
            self.category(new Category(cat, 0, cat.charAt(0).toUpperCase() + cat.slice(1) + 's'));
        } else {
            self.category(new Category('total', 0, 'Total'));
        }
    };

    self.sortOrder.subscribe(function(newValue) {
        if (self.syncSortOrder === true) {
            self.submit();
        }
    });

    self.setSortOrder = function(sort_name) {
        self.syncSortOrder = false;
        if (sort_name !== undefined && sort_name !== null && sort_name !== '') {
            self.sortOrder(sort_name);
        } else {
            self.sortOrder('modified_desc');
        }
        self.syncSortOrder = true;
    };

    self.setSortOrderSettings = function(category_name) {
        self.syncSortOrder = false;
        self.sortOrderSettings(SortOrderSettings(category_name));
        self.syncSortOrder = true;
    };

    self.resultsPerPage.subscribe(function(newValue) {
        if (self.syncResultsPerPage === true) {
            self.submit();
        }
    });

    self.setResultsPerPage = function(size) {
        self.syncResultsPerPage = false;
        if (size !== undefined && size !== null && size !== '') {
            if (Number.isInteger(size) === true) {
                self.resultsPerPage(Number(size));
            } else {
                self.resultsPerPage(10);
            }
        }
        self.syncResultsPerPage = true;
    };

    self.currentPage.subscribe(function(newValue) {
        var value = self.currentPage();
        if (typeof value === 'string') {
            var intValue = Number(value);
            if (Number.isInteger(intValue)) {
                if (intValue < 1) {
                    intValue = 1;
                }

                if (intValue > self.totalPages()) {
                    intValue = self.totalPages();
                }

                self.currentPage(intValue);
            } else {
                self.currentPage(1);
            }
        }
    });

    self.isCurrentPage = function(val) {
        return self.currentPage() === val;
    };

    self.getHighlightLimit = function() {
        var limits = ['title:' + self.titleLengthLimit + ',',
                      'name:' + self.nameLengthLimit + ',',
                      'user:' + self.usernameLnegthLimit + ',',
                      'text:' + self.textLengthLimit + ',',
                      'comments.*:' + self.commentLengthLimit];
        return limits.join('');
    };

    self.toDate = function(val) {
        var date = new Date(val);
        return [date.getFullYear(), date.getMonth() + 1, date.getDate()].join('/');
    };

    self.makeTitle = function(originalStr, highlightArray, limit) {
        if (highlightArray !== undefined) {
            var highlightStr = highlightArray[0];
            var extracted = highlightStr.replace(/<b>/gi,'').replace(/<\/b>/gi, '');
            if (originalStr === extracted) {
                return highlightStr;
            }

            var title = '';
            var subStrPos = originalStr.indexOf(extracted);
            if (subStrPos > 0) {
                title += '...';
            }

            title += highlightStr;

            if (originalStr.length > (subStrPos + extracted.length)) {
                title += '...';
            }

            return title;
        }

        if (originalStr.length > limit) {
            return originalStr.substr(0, limit) + '...';
        }

        return originalStr;
    };

    self.makeTitleWithExtension = function(originalStr, highlightArray, limit) {
        var ext = '';
        var extWithTag = '';
        var extPos = originalStr.lastIndexOf('.');
        if (extPos >= 0) {
            ext = originalStr.substr(extPos);
            extWithTag = '<font color="#C0C0C0">' + ext + '</font>';
        }

        if (highlightArray !== undefined) {
            var highlightStr = highlightArray[0];
            var extracted = highlightStr.replace(/<b>/gi,'').replace(/<\/b>/gi, '');
            var highlightExtPos = highlightStr.lastIndexOf('.');

            // check exact match
            if (originalStr === extracted) {
                if (highlightExtPos < 0) {
                    return highlightStr;
                }

                return highlightStr.substr(0, highlightExtPos) + extWithTag;
            }

            var title = '';
            // check forward match
            var subStrPos = originalStr.indexOf(extracted);
            if (subStrPos > 0) {
                title += '...';
            }

            // check backward match
            if (originalStr.length === (subStrPos + extracted.length)) {
                if (highlightExtPos < 0) {
                    return title + highlightStr;
                }

                return title + highlightStr.substr(0, highlightExtPos) + extWithTag;
            }

            // check extension
            if (extPos < 0) {
                return title + highlightStr + '...';
            }

            var diffFromExtPos = (originalStr.length - ext.length) - (subStrPos + extracted.length);

            // words including an extension lack
            if (diffFromExtPos > 0) {
                return title + highlightStr + '... ' + extWithTag;
            }

            // only an extension missed
            if (diffFromExtPos === 0) {
                return title + highlightStr + extWithTag;
            }

            // highlight includes a partial extension
            return title + highlightStr.substr(0, highlightStr.length + diffFromExtPos) + extWithTag;
        }

        if (originalStr.length > limit) {
            // no extension
            if (extPos < 0) {
                return originalStr.substr(0, limit) + '...';
            }

            return originalStr.substr(0, limit) + '... ' + extWithTag;
        } else {
            // no extension
            if (extPos < 0) {
                return originalStr;
            }

            return originalStr.substr(0, extPos) + extWithTag;
        }
    };

    self.getProjectName = function(result) {
        var originalStr = result.title;
        var highlightArray = result.highlight.title;
        var lengthLimit = self.titleLengthLimit;
        return self.makeTitle(originalStr, highlightArray, lengthLimit);
    };

    self.getFileName = function(result) {
        var originalStr = result.name;
        var highlightArray = result.highlight.name;
        var lengthLimit = self.nameLengthLimit;
        return self.makeTitleWithExtension(originalStr, highlightArray, lengthLimit);
    };

    self.getUserName = function(result) {
        var originalStr = result.user;
        var highlightArray = result.highlight.user;
        var lengthLimit = self.titleLengthLimit;
        return self.makeTitle(originalStr, highlightArray, lengthLimit);
    };

    self.getWikiName = function(result) {
        var originalStr = result.name;
        var highlightArray = result.highlight.name;
        var lengthLimit = self.titleLengthLimit;
        return self.makeTitle(originalStr, highlightArray, lengthLimit);
    };

    self.makeText = function(text) {
        var extracted = text.replace(/<b>/gi,'').replace(/<\/b>/gi, '');
        if (extracted.length >= self.textLengthLimit) {
            return text.substr(0, self.textLengthLimit) + '...';
        }

        return text;
    };

    self.makeComment = function(comment) {
        var extracted = comment.replace(/<b>/gi,'').replace(/<\/b>/gi, '');
        if (extracted.length >= self.commentLengthLimit) {
            return comment.substr(0, self.commentLengthLimit) + '...';
        }

        return comment;
    };

    self.getGuidText = function(guid) {
        return guid.toUpperCase().split('/').join('');
    };

    self.getGuidUrl = function(guid) {
        return window.location.origin + '/' + guid.split('/').join('') + '/';
    };

};

function Search(selector, url, appURL) {
    // Initialization code
    var self = this;

    self.viewModel = new ViewModel({'url': url, 'appURL': appURL});
    History.Adapter.bind(window, 'statechange', self.viewModel.pageChange);

    var data = {
        query: $osf.urlParams().q,
        page: Number($osf.urlParams().page),
        scrollTop: 0,
        filter: $osf.urlParams().filter
    };
    //Ensure our state keeps its URL paramaters
    History.replaceState(data, _('GakuNin RDM | Search'), location.search);
    //Set out observables from the newly replaced state
    self.viewModel.loadState();
    //Preform search from url params
    self.viewModel.search(true, true);

    $osf.applyBindings(self.viewModel, selector);
}

module.exports = Search;
