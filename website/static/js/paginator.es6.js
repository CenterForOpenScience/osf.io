var ko = require('knockout');

var MAX_PAGES_ON_PAGINATOR = 7;
var MAX_PAGES_ON_PAGINATOR_SIDE = 5;    

class Pagintor {
    constructor() {
        this.numberOfPages = ko.observable(0);
        this.currentPage = ko.observable(0);
        this.paginators = ko.observableArray([]);
        if (!this.search){
            throw 'Subclasses of Paginator must implement a \'search\' function';
        }
    }
    addNewPaginators() {
        vm = this;
        vm.paginators.removeAll();
        if (vm.numberOfPages() > 1) {
            vm.paginators.push({
                style: (vm.currentPage() === 0) ? 'disabled' : '',
                handler: vm.previousPage,
                text: '&lt;'
            });
            vm.paginators.push({
                style: (vm.currentPage() === 0) ? 'active' : '',
                text: '1',
                handler: function() {
                    vm.currentPage(0);
                    vm.search();
                }
            });
            if (vm.numberOfPages() <= MAX_PAGES_ON_PAGINATOR) {
                for (var i = 1; i < vm.numberOfPages() - 1; i++) {
                    vm.paginators.push({
                        style: (vm.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            vm.currentPage(parseInt(this.text) - 1);
                            vm.search();
                        }
                    });
                }
            } else if (vm.currentPage() < MAX_PAGES_ON_PAGINATOR_SIDE - 1) { // One ellipse at the end
                for (var i = 1; i < MAX_PAGES_ON_PAGINATOR_SIDE; i++) {
                    vm.paginators.push({
                        style: (vm.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            vm.currentPage(parseInt(this.text) - 1);
                            vm.search();
                        }
                    });
                }
                vm.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
            } else if (vm.currentPage() > vm.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE) { // one ellipses at the beginning
                vm.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
                for (var i = vm.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE; i < vm.numberOfPages() - 1; i++) {
                    vm.paginators.push({
                        style: (vm.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            vm.currentPage(parseInt(this.text) - 1);
                            vm.search();
                        }
                    });
                }
            } else { // two ellipses
                vm.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
                for (var i = vm.currentPage() - 1; i <= vm.currentPage() + 1; i++) {
                    vm.paginators.push({
                        style: (vm.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            vm.currentPage(parseInt(this.text) - 1);
                            vm.search();
                        }
                    });
                }
                vm.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
            }
            vm.paginators.push({
                style: (vm.currentPage() === vm.numberOfPages() - 1) ? 'active' : '',
                text: vm.numberOfPages(),
                handler: function() {
                    vm.currentPage(vm.numberOfPages() - 1);
                    vm.search();
                }
            });
            vm.paginators.push({
                style: (vm.currentPage() === vm.numberOfPages() - 1) ? 'disabled' : '',
                handler: vm.nextPage,
                text: '&gt;'
            });
        }
    }
    nextPage(){
        this.currentPage(this.currentPage() + 1);
        this.search();
    }
    previousPage(){
        this.currentPage(this.currentPage() - 1);
        this.search();
    }
}
