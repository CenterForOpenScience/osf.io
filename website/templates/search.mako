<%inherit file="base.mako"/>
<%def name="title()">Search</%def>
<%def name="content()">
    <link href="//maxcdn.bootstrapcdn.com/font-awesome/4.2.0/css/font-awesome.min.css" rel="stylesheet">
    <script>
        $('input[name=q]').remove();
    </script>
    <div id="searchControls">
        <div class="row">
            <div class="col-md-12">
                <form class="input-group" data-bind="submit: submit">
                    <input type="text" class="form-control" placeholder="Search" data-bind="value: query">
                    <span class="input-group-btn">
                        <button type=button class="btn btn-default" data-bind="click: help"><i class="icon-question"></i></button>
                        <button type=button class="btn btn-default" data-bind="click: submit"><i class="icon-search"></i></button>
                    </span>
                </form>
            </div>
        </div>

        <br />

        <div class="row">
            <!-- ko if: categories().length > 1-->
            <div class="col-md-3 hidden" data-bind="css: {hidden: categories().length < 1 }">
                <ul class="nav nav-pills nav-stacked" data-bind="foreach: categories">
                    <!-- ko if: count() > 0 -->
                        <!-- ko if: $parent.alias().indexOf(alias()) !== -1 -->
                            <li class="active">
                                <a data-bind="click: $parent.filter.bind($data)">{{ name() }}<span class="badge pull-right">{{count()}}</span></a>
                            </li>
                        <!-- /ko -->
                        <!-- ko if: $parent.alias().indexOf(alias()) == -1 -->
                            <li>
                                <a data-bind="click: $parent.filter.bind($data)">{{ name() }}<span class="badge pull-right">{{count()}}</span></a>
                            </li>
                        <!-- /ko -->
                    <!-- /ko -->
                </ul>
            </div>
            <!-- /ko -->

            <div class="col-md-9">
                <!-- ko if: searchStarted() && !totalCount() -->
                <div class="results hidden" data-bind="css: {hidden: totalCount() }">No results found.</div>
                <!-- /ko -->

                <div data-bind="foreach: results">
                    <div class="well" data-bind="template: { name: category, data: $data }"></div>
                </div>
                <div class="navigation-controls hidden" data-bind="css: {hidden: totalPages() <= 1 }">
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

    <script type="text/html" id="metadata">
        <!-- ko if: $data.links -->
            <h4><a data-bind="attr.href: links[0].url">{{ title }}</a></h4>
        <!-- /ko -->

        <!-- ko ifnot: $data.links -->
            <h4><a data-bind="attr.href: id.url">{{ title }}</a></h4>
        <!-- /ko -->

        <h5>Description: <small>{{ description | default:"No Description" | fit:500}}</small></h5>

        <!-- ko if: contributors.length > 0 -->
        <h5>
            Contributors: <small data-bind="foreach: contributors">
                <span>{{ $data }}</span>
            <!-- ko if: ($index()+1) < ($parent.contributors.length) -->&nbsp;- <!-- /ko -->
            </small>
        </h5>
        <!-- /ko -->

        <!-- ko if: $data.source -->
        <h5>Source: <small>{{ source }}</small></h5>
        <!-- /ko -->

        <!-- ko if: $data.isResource -->
        <button class="btn btn-primary pull-right" data-bind="click: $parents[1].claim.bind($data, _id)">Curate This</button>
        <br>
        <!-- /ko -->
    </script>
    <script type="text/html" id="user">
        <h4><a data-bind="attr.href: url"><span>{{ user }}</span></a></h4>
        <span data-bind="visible: job_title, text: job_title"></span><!-- ko if: job_title && job --> at <!-- /ko -->
        <span data-bind="visible: job, text: job"></span><!-- ko if: job_title || job --><br /><!-- /ko -->
        <span data-bind="visible: degree, text: degree"></span><!-- ko if: degree && school --> from <!-- /ko -->
        <span data-bind="visible: school, text: school"></span><!-- ko if: degree || school --><br /><!-- /ko -->
        <!-- ko if social -->
        <ul class="list-inline">
            <li data-bind="visible: social.personal">
                <a data-bind="attr.href: social.personal"><i class="fa fa-globe"></i></a>
            </li>
            <li data-bind="visible: social.twitter">
                <a data-bind="attr.href: social.twitter"><i class="fa fa-twitter"></i></a>
            </li>
            <li data-bind="visible: social.github">
                <a data-bind="attr.href: social.github"><i class="fa fa-github-alt"></i></a>
            </li>
            <li data-bind="visible: social.linkedIn">
                <a data-bind="attr.href: social.linkedIn"><i class="fa fa-linkedin"></i></a>
            </li>
            <li data-bind="visible: social.scholar">
                <a data-bind="attr.href: social.scholar"><img height=14 src="/static/img/googlescholar.png"></a>
            </li>
            <li data-bind="visible: social.impactStory">
                <a data-bind="attr.href: social.impactStory"><i class="fa fa-info-circle"></i></a>
            </li>
            <li data-bind="visible: social.orcid">
                <a data-bind="attr.href: social.orcid"><i class="fa">iD</i></a>
            </li>
            <li data-bind="visible: social.researcherId">
                <a data-bind="attr.href: social.researcherId"><i class="fa">R</i></a>
            </li>
        </ul>
        <!-- /ko -->
    </script>
    <script type="text/html" id="project">
        <h4><a data-bind="attr.href: url">{{title }}</a></h4>
        <h5>Description: <small>{{ description | default:"No Description" | fit:500 }}</small></h5>

        <!-- ko if: contributors.length > 0 -->
        <h5>
            Contributors: <small data-bind="foreach: contributors">
                <a data-bind="attr.href: $parent.contributors_url[$index()]">{{ $data }}</a>
            <!-- ko if: ($index()+1) < ($parent.contributors.length) -->&nbsp;- <!-- /ko -->
            </small>
        </h5>
        <!-- /ko -->
    </script>
    <script type="text/html" id="app">
        <h4><a data-bind="attr.href: url">{{title }}</a></h4>
        <h5>Description: <small>{{ description | default:"No Description" | fit:500 }}</small></h5>

        <!-- ko if: contributors.length > 0 -->
        <h5>
            Contributors: <small data-bind="foreach: contributors">
                <a data-bind="attr.href: $parent.contributors_url[$index()]">{{ $data }}</a>
            <!-- ko if: ($index()+1) < ($parent.contributors.length) -->&nbsp;- <!-- /ko -->
            </small>
        </h5>
        <!-- /ko -->
    </script>
    <script type="text/html" id="component">
        <h4><a data-bind="attr.href: parent_url">{{ parent_title}}</a> / <a data-bind="attr.href: url">{{title }}</a></h4>
        <h5>Description: <small>{{ description | default:"No Description" | fit:500 }}</small></h5>

        <!-- ko if: contributors.length > 0 -->
        <h5>
            Contributors: <small data-bind="foreach: contributors">
                <a data-bind="attr.href: $parent.contributors_url[$index()]">{{ $data }}</a>
            <!-- ko if: ($index()+1) < ($parent.contributors.length) -->&nbsp;- <!-- /ko -->
            </small>
        </h5>
        <!-- /ko -->
    </script>
    <script type="text/html" id="registration">
        <h4><a data-bind="attr.href: url">{{title }}</a></h4>
        <h5>Description: <small>{{ description | default:"No Description" | fit:500 }}</small></h5>

        <!-- ko if: contributors.length > 0 -->
        <h5>
            Contributors: <small data-bind="foreach: contributors">
                <a data-bind="attr.href: $parent.contributors_url[$index()]">{{ $data }}</a>
            <!-- ko if: ($index()+1) < ($parent.contributors.length) -->&nbsp;- <!-- /ko -->
            </small>
        </h5>
        <!-- /ko -->
    </script>
</%def>

<%def name="javascript_bottom()">

        <script type='text/javascript'>
            $script(['/static/js/search.js'], function(){
            var search =  new Search('#searchControls', '/api/v1/search/', '');
            });
        </script>


</%def>
