<%inherit file="base.mako"/>
<%def name="title()">SHARE Search</%def>
<%def name="content()">
    <div id="searchControls">
        <div class="row">
            <div class="col-md-8 col-md-offset-1">
                    <div id="searchBox">
                        <!--<form class="form-search" action="http://localhost:80/api/search" method="get" role="search">-->
                        <form class="form-inline" data-bind= "submit: submit" role="form">
                            <div class="form-group">
                                <input type="text" class="form-control" placeholder="SHARE Search" data-bind= "value: query" name="q">
                            </div>
                            <button type="submit" class="btn btn-default">Search</button>
                        </form>
                    </div>
                </div>
            </div>
        <div class="row">
            <div class="col-md-8 col-md-offset-1">
                    <div class="navigation-controls hidden" data-bind="css: {hidden: totalPages() < 0 }">
                        <span data-bind="visible: prevPageExists">
                            <a href="#" data-bind="click: pagePrev">Previous Page</a> -
                        </span>
                        <span data-bind="visible: totalPages() > 0">
                            <span data-bind="text: navLocation"></span>
                        </span>
                        <span data-bind="visible: nextPageExists"> -
                            <a href="#" data-bind="click: pageNext">Next Page </a>
                        </span>
                    </div>
                    <div class="results hidden" data-bind="foreach: results, css: {hidden: totalResults() == 0}">
                        <div class="result">
                            <!-- ko if: url() -->
                                <span class="title"><h4><a data-bind='attr:{href: url}'><span data-bind='text:title'></span></a></h4></span>
                            <!-- /ko -->
                            <!-- ko ifnot: url() -->
                                <span class="title"><h4><span data-bind='text:title'></span></h4></span>
                            <!-- /ko -->
                            <!-- ko if: description() -->
                            <strong>Description:</strong>&nbsp;<span class="description" data-bind="text: description"></span><br />
                            <!-- /ko -->
                            <!-- ko if: contributors().length -->
                            <strong>Contributors:</strong>&nbsp;<span class="search-result-contributors" data-bind="foreach: contributors">
                                <span class="name" data-bind="text: fullname"></span>
                                <!-- ko if: $index()+1 < $parent.contributors().length -->&nbsp;- <!-- /ko -->
                                </span> <br />
                            <!-- /ko -->
                            <!-- ko if: source -->
                                <strong>Source:</strong>&nbsp;<span data-bind="text: source"><br/></span>
                            <!-- /ko -->
                        </div>
                    </div>
                    <div class="navigation-controls hidden" data-bind="css: {hidden: totalPages() < 0 }">
                        <span data-bind="visible: prevPageExists">
                            <a href="#" data-bind="click: pagePrev">Previous Page</a> -
                        </span>
                        <span data-bind="visible: totalPages() > 0">
                            <span data-bind="text: navLocation"></span>
                        </span>
                        <span data-bind="visible: nextPageExists"> -
                            <a href="#" data-bind="click: pageNext">Next Page </a>
                        </span>
                    </div>


                    <div class="buffer"></div>
            </div><!--col-->
        </div><!--row-->
    </div> <!--SearchControls-->
</%def>

<%def name="javascript_bottom()">

        <script type='text/javascript'>
            $script(['/static/js/shareSearch.js'], function(){
                var shareSearch =  new ShareSearch('#searchControls', '/api/v1/app/6qajn/');
            });
        </script>


</%def>