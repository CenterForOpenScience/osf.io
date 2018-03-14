'use strict';
var $osf = require('js/osfHelpers');

var buildPaginationArray = function(currentPageNumber, totalPages) {
    /**
     * Returns an array of page numbers for pagination in UI. Creates similar UI
     * to ember addon https://github.com/mharris717/ember-cli-pagination
     * For example: [1, 2, '...', 23, 24, 25, 26], where current page is 25.
     * Or, [1, 2, '...', 6, 7, 8, 9, 10, '...', 25, 26], where current page is 8.
     *
     * @param {integer} currentPageNumber: current page of results being displayed
     * @param {integer} totalPages: total number of pages available
     * @returns {array} array of pages to display
     **/

    // Pagination available will always include the first two and last two pages
    var start = [1, 2];
    var end = [totalPages - 1, totalPages];

    // Middle range of pagination available will take the form:
    // [current - 2, current - 1, current, current + 1, current + 2]
    var middle = [];
    for (var pageNum = currentPageNumber - 2; pageNum <= currentPageNumber + 2; pageNum++) {
        if (pageNum > 2 && pageNum < totalPages - 1) {
            middle.push(pageNum);
        }
    }

    // If there is a gap between the start range and the middle range, add a '...'
    if (!middle || middle[0] !== 3) {
        middle.unshift('...');
    }

    // If gap between middle and end ranges, add a '...'
    if (!middle || (middle[middle.length - 1] !== '...' && middle[middle.length - 1] !== (totalPages - 2))) {
        middle.push('...');
    }
    // Now flatten the start, middle, and end lists into one! This is your pagination array.
    return [].concat(start, middle, end);
}

var pageIsDisabled = function(pageNum, hasPrevious, hasNext) {
    /**
     * Should page link be disabled? Previous and next links are disabled if there
     * is no previous or next page. Truncated pages, signified by '...', are also disabled.
     *
     * @param {integer} currentPageNumber: current page of results being displayed
     * @param {boolean} hasPrevious: is there a previous page?
     * @param {boolean} hasNext: is there a next page?
     * @returns {boolean} whether page should be disabled
     **/
    return pageNum === '...' || ((pageNum === '«' && !hasPrevious) || (pageNum === '»' && !hasNext));
}
var PaginationViewModel = function(currentPageNumber, totalPages, q, sort, hasPrevious, hasNext) {
    /**
     * Returns an array of dictionaries for building pagination
     *
     * @param {integer} currentPageNumber: current page of results being displayed
     * @param {integer} totalPages: total number of pages available
     * @param {string} q: query param
     * @param {string} sort: query param
     * @param {boolean} hasPrevious: is there a previous page?
     * @param {boolean} hasNext: is there a next page?
     * @returns {array} pagination array of dictionaries for each page visible
     **/
    var self = this;
    var pagination = [];
    if (totalPages <= 4) {
        // Where we only have a few pages and don't need to truncate any
        for (var i = 1; i <= totalPages; i++) {
           pagination.push(i);
        }
    } else {
        pagination = buildPaginationArray(currentPageNumber, totalPages);
    }

    pagination.unshift('«');
    pagination.push('»');

    self.pagination = [];
    for (var i = 0; i <= pagination.length - 1; i++) {
        var pageNum = pagination[i];
        var isCurrent = pageNum === currentPageNumber;
        var isDisabled = pageIsDisabled(pageNum, hasPrevious, hasNext);
        var href = "";
        if (!isCurrent && !isDisabled) {
            if (pageNum === '«') {
                pageNum = currentPageNumber - 1;
            }
            if (pageNum === '»') {
                pageNum = currentPageNumber + 1;
            }
            href = "?page=" + pageNum + "&q=" + q + "&sort=" + sort;
        }
        self.pagination.push({
            isCurrent: isCurrent,
            isDisabled: isDisabled,
            href: href,
            page: pagination[i],
        });
    }
}

var Pagination = function(selector, currentPageNumber, totalPages, q, sort, hasPrevious, hasNext) {
    this.viewModel = new PaginationViewModel(currentPageNumber, totalPages, q, sort, hasPrevious, hasNext);
    $osf.applyBindings(this.viewModel, selector);
    window.pagination = this.viewModel;
}

module.exports = Pagination;
