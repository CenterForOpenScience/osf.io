;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'zeroclipboard', 'osfutils'], factory);
    } else {
        global.PrivateLinkTable  = factory(ko, jQuery, ZeroClipboard);
    }
}(this, function(ko, $, ZeroClipboard) {

    // Make sure ZeroClipboard finds the right flash file
    ZeroClipboard.config({
        moviePath: '/static/vendor/bower_components/zeroclipboard/ZeroClipboard.swf'}
    );

    var client = new ZeroClipboard( document.getElementsByClassName("copy-button") );
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
  } );

    function ViewModel(url) {
        var self = this;
        self.url = url;
        self.private_links = ko.observableArray();
        self.node_url = ko.observable(null);

        function onFetchSuccess(response) {
            var node = response.node;
            self.private_links(node.private_links);
            self.node_url(node.absolute_url);
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
                        data: JSON.stringify(data_to_send)
                    }).done(function(response) {
                        window.location.reload();
                    });
                }
             });
        };

    }



    $('tbody .link-create-date').each(function(idx, elem) {
         var e = $(elem);
         var dt = new $.osf.FormattableDate(e.text());
         e.text(dt.local);
         e.tooltip({
             title: dt.utc,
             container: "body"
         });
     });

    function PrivateLinkTable (selector, url) {
        var self = this;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);
        window.viewModel = self.viewModel;
    }

    return PrivateLinkTable;

}));
