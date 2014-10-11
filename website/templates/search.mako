<%inherit file="base.mako"/>
<%def name="title()">Search</%def>
<%def name="content()">
    <script>
        $('input[name=q]').remove();
    </script>
    <div id="searchControls">
        <div class="row">
            <div class="col-md-12">
                <form class="input-group" data-bind="submit: submit">
                    <input type="text" class="form-control" placeholder="Search" data-bind="value: query">
                    <span class="input-group-btn">
                        <button type=button class="btn btn-default" data-bind="click: submit"><i class="icon-search"></i></button>
                    </span>
                </form>
            </div>
        </div>

        <br />

        <div class="row">
            <!-- ko if: categories().length > 1-->
            <div class="col-md-3" data-bind="css: {hidden: categories().length < 1 }">
                <ul class="nav nav-pills nav-stacked" data-bind="foreach: categories">
                    <li><a>{{ name() }}<span class="badge pull-right">{{count()}}</span></a></li>
                </ul>
            </div>
            <!-- /ko -->

            <div class="col-md-9">
                <!-- ko if: searchStarted() && !totalResults() -->
                <div class="results">No results found.</div>
                <!-- /ko -->

                <div data-bind="foreach: results">
                    <div class="well" data-bind="template: { name: category, data: $data }"></div>
                    <br />
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
    </div>

    <script type="text/html" id="category">

    </script>
    <script type="text/html" id="metadata">
        <!-- ko if: $data.links -->
            <span class="title"><h4><a data-bind="attr.href: links[0].url"><span>{{ title }}</span></a></h4></span>
        <!-- /ko -->

        <!-- ko ifnot: $data.links -->
            <span class="title"><h4><a data-bind="attr.href: id.url"><span>{{ title }}</span></a></h4></span>
        <!-- /ko -->

        <strong>Description:</strong>&nbsp;<span class="description">{{ description | default:"No Description" | fit:500}}</span>

        <br />

        <!-- ko if: contributors.length > 0 -->
        <strong>Contributors:</strong>&nbsp;<span class="search-result-contributors" data-bind="foreach: contributors">
            <span class="name">{{ $data }}</span>
            <!-- ko if: ($index()+1) < ($parent.contributors.length) -->&nbsp;- <!-- /ko -->
        </span>

        <br />

        <!-- /ko -->

        <!-- ko if: $data.source -->
        <strong>Source:</strong>&nbsp;<span>{{ source }}<br/></span>
        <!-- /ko -->
    </script>
    <script type="text/html" id="user">
        <span class="title"><h4><a data-bind="attr.href: url"><span>{{ user }}</span></a></h4></span>
    </script>
    <script type="text/html" id="project">
        <span class="title"><h4><a data-bind="attr.href: url"><span>{{ title }}</span></a></h4></span>

        <strong>Description:</strong>&nbsp;<span class="description">{{ description | default:"No Description" | fit:500 }}</span>

        <br />

        <!-- ko if: contributors.length > 0 -->
        <strong>Contributors:</strong>&nbsp;<span class="search-result-contributors" data-bind="foreach: contributors">
            <span class="name"><a data-bind="attr.href: $parent.contributors_url[$index()]">{{ $data }}</a></span>
            <!-- ko if: ($index()+1) < ($parent.contributors.length) -->&nbsp;- <!-- /ko -->
        </span>
        <!-- /ko -->
    </script>
    <script type="text/html" id="component">
        <span class="title"><h4><a data-bind="attr.href: url"><span>{{ title }}</span></a></h4></span>
        <span class="title"><h5><a data-bind="attr.href: parent_url"><span>{{ parent_title }}</span></a></h5></span>
        <strong>Description:</strong>&nbsp;<span class="description">{{ description | default:"No Description" | fit:500 }}</span>

        <br />

        <!-- ko if: contributors.length > 0 -->
        <strong>Contributors:</strong>&nbsp;<span class="search-result-contributors" data-bind="foreach: contributors">
            <span class="name"><a data-bind="attr.href: $parent.contributors_url[$index()]">{{ $data }}</a></span>
            <!-- ko if: ($index()+1) < ($parent.contributors.length) -->&nbsp;- <!-- /ko -->
        </span>
        <!-- /ko -->
    </script>
    <script type="text/html" id="registration">
        <span class="title"><h4><a data-bind="attr.href: url"><span>{{ title }}</span></a></h4></span>
        <span class="title"><h5><a data-bind="attr.href: parent_url"><span>{{ parent_title }}</span></a></h5></span>
        <strong>Description:</strong>&nbsp;<span class="description">{{ description | default:"No Description" | fit:500 }}</span>

        <br />

        <!-- ko if: contributors.length > 0 -->
        <strong>Contributors:</strong>&nbsp;<span class="search-result-contributors" data-bind="foreach: contributors">
            <span class="name"><a data-bind="attr.href: $parent.contributors_url[$index()]">{{ $data }}</a></span>
            <!-- ko if: ($index()+1) < ($parent.contributors.length) -->&nbsp;- <!-- /ko -->
        </span>
        <!-- /ko -->
    </script>
</%def>

<%def name="javascript_bottom()">

        <script type='text/javascript'>
            $script(['/static/js/search.js'], function(){
            var search =  new Search('#searchControls', '/api/v1/search/');
            });
        </script>


</%def>
