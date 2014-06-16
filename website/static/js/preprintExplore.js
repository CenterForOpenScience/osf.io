;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'knockoutpunches'], factory);
    } else if (typeof $script === 'function') {
        global.PreprintModel  = factory(ko, jQuery);
        $script.done('PreprintModel');
    } else {
        global.PreprintModel  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    ko.punches.enableAll();
    ko.punches.attributeInterpolationMarkup.enable();

    function Disciplince(top, kids) {
        var self = this;
        self.topDisciplince = top;
        self.children = kids;
        self.topDisciplinceFormatted = top.split(' ').join('-');
    };

    function PreprintViewModel(url) {
        var self = this;
        self.url = url;
        self.disciplines = ko.observableArray([]);

        function onFetchSuccess(response) {
            self.disciplines(ko.utils.arrayMap(Object.keys(response.disciplines), function(key) {
                return new Disciplince(key, response.disciplines[key]);
            }));
        }

        function onFetchError() {
          //TODO
          console.log('an error occurred');
        }

        function fetch() {
            $.ajax({url: self.url, type: 'GET', dataType: 'json',
                success: onFetchSuccess,
                error: onFetchError
            });
        }

        fetch();
    }

    function PreprintModel(url, div) {
        var self = this;
        $.osf.applyBindings(PreprintViewModel(url), div);
        window.PreprintViewModel = PreprintViewModel;
    }

    return PreprintModel;
}));
