// main.js
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout', 'zeroclipboard', 'osfutils'], factory);
    } else {
        global.PrivateLinkManager  = factory(jQuery, ko, ZeroClipboard);
    }
}(this, function($, ko, ZeroClipboard) {

    var NODE_OFFSET = 25;
    var PrivateLinkViewModel = function(url) {
        var self = this;

        // URL for the private links endpoint that returns:
        // {
        //   'result': {
        //      'node': {
        //          'title': ..node title..
        //          'parentId':  .. parent ID..
        //          'parentTitle': .. parent Title ..
        //      },
        //      children: [{indent: ..., id: ......}]
        //   }
        // }
        self.url = url;
        self.title = ko.observable('');
        self.parentId = ko.observable(null);
        self.parentTitle = ko.observable(null);
        self.label = ko.observable(null);
        self.pageTitle = 'Generate New Private Link';
        self.errorMsg = ko.observable('');

        self.nodes = ko.observableArray([]);
        self.nodesToChange = ko.observableArray();

        /**
         * Fetches the node info from the server and updates the viewmodel.
         */

        function onFetchSuccess(response) {
            var nodeData = response.result.node;
            self.title(node.title);
            self.parentId(node.parentId);
            self.parentTitle(node.parentTitle);
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
            // TODO: Get rid of me
            $.getJSON(
                nodeApiUrl + 'get_editable_children/',
                {},
                function(result) {
                    $.each(result['children'], function(idx, child) {
                        child['margin'] = NODE_OFFSET + child['indent'] * NODE_OFFSET + 'px';
                    });
                    self.nodes(result['children']);
                }
            );
        }

        // Initial fetch of data
        fetch();



        self.cantSelectNodes = function() {
            return self.nodesToChange().length == self.nodes().length;
        };
        self.cantDeselectNodes = function() {
            return self.nodesToChange().length == 0;
        };

        self.selectNodes = function() {
            self.nodesToChange(attrMap(self.nodes(), 'id'));
        };
        self.deselectNodes = function() {
            self.nodesToChange([]);
        };

        self.submit = function() {
            $.ajax(
                nodeApiUrl + 'private_link/',
                {
                    type: 'post',
                    data: JSON.stringify({
                        node_ids: self.nodesToChange(),
                        label: self.label()
                    }),
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        if (response.status === 'success') {
                            window.location.reload();
                        }
                    }
                }
            )
        };

        self.clear = function() {
            self.nodesToChange([]);
        };
    };


    function PrivateLinkManager (selector, url) {

    }


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
    return PrivateLinkManager;

}));
