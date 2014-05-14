;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'zeroclipboard', 'osfutils'], factory);
    } else {
        $script.ready(['zeroclipboard'], function (){
            global.PrivateLinkTable  = factory(ko, jQuery, ZeroClipboard);
            $script.done('privateLinkTable');
        });
    }
}(this, function(ko, $, ZeroClipboard) {

    // Make sure ZeroClipboard finds the right flash file
    ZeroClipboard.config({
        moviePath: '/static/vendor/bower_components/zeroclipboard/ZeroClipboard.swf'}
    );

    var updateClipboard = function(target) {

        var client = new ZeroClipboard( target );

        client.on( "load", function(client) {
        // alert( "movie is loaded" );

            client.on( "complete", function(client, args) {
              // `this` is the element that was clicked
                this.blur();
            } );

            client.on("mousedown", function(client,args){
                $(this).addClass("active");
            });

            client.on("mouseup", function(client,args){
                $(this).removeClass("active");
            });

            client.on("mouseover", function(client,args){
                $(this).tooltip("show");
            });

            client.on("mouseout", function(client,args){
                $(this).tooltip("hide");
            });
        });

    };

    function LinkViewModel(data, $root) {

        var self = this;

        self.$root = $root;
        $.extend(self, data);
        self.dateCreated = new $.osf.FormattableDate(data.date_created);
        self.linkUrl = ko.computed(function(){
            return self.$root.nodeUrl() + "?key=" + data.key
        });

    }

    function ViewModel(url) {
        var self = this;
        self.url = url;
        self.privateLinks = ko.observableArray();
        self.nodeUrl = ko.observable(null);

        function onFetchSuccess(response) {
            var node = response.node;
            self.privateLinks(ko.utils.arrayMap(node.private_links, function(link) {
                return new LinkViewModel(link, self);
            }));
            self.nodeUrl(node.absolute_url);
        }

        function onFetchError() {
          //TODO
          console.log('an error occurred');
        }

        function fetch() {
            $.ajax({url: url, type: 'GET', dataType: 'json',
              success: onFetchSuccess,
              error: onFetchError
            });
        }

        fetch();

        self.removeLink = function(data){
            var data_to_send={
                'private_link_id': data.id
            };
            bootbox.confirm('Are you sure to remove this private link?', function(result) {
                if (result) {
                    $.ajax({
                        type: "delete",
                        url: nodeApiUrl + "private_link/",
                        contentType: "application/json",
                        dataType: "json",
                        data: JSON.stringify(data_to_send),
                        success: function(response) {
                            self.privateLinks.remove(data);
                        },
                        error: function(xhr) {
                            bootbox.alert("Failed to delete the private link.")
                        }
                    });
                }
             });
        };

        self.updateClipboard = function(elm) {

            var $tr = $(elm);
            // Add this to client
            var target = $tr.find('.copy-button');
            updateClipboard(target);
            $tr.find('.remove-private-link').tooltip();
        };

    }

    function PrivateLinkTable (selector, url) {
        var self = this;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);

    }
    return PrivateLinkTable;

}));
