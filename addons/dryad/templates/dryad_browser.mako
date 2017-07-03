



<div>
    <!-- Search Bar-->
    <div class="pull-left">
        <form data-bind="submit: search">
            <input id="search_terms"
                type="text"
                data-bind="value: searchTerms, enterkey: search"
                placeholder="Search Archive">
            </input>
            <button class="btn btn-default">
                Search
            </button>
        </form>

    </div>

    <!-- Results-->
    <div class="pull-right">
        <button class="btn btn-default" data-bind="click: getPrevious">
            Prev
        </button>
        <button class="btn btn-default" data-bind="click: getNext" >
        Next
        </button>
        Viewing
        <span data-bind="text: firstIndex"></span>
        -
        <span data-bind="text: lastIndex"></span>
        of
        <span data-bind="text: totalResults"></span>
    </div>
</div><br/>
<hr/>

<!-- Spinner Placeholder-->
<div id="browser_loading"
    class="spinner-loading-wrapper">
    <div class="logo-spin logo-lg"></div>
    <p class="m-t-sm fg-load-message">
        Loading Archive...
    </p>
</div>
<div id="browser_wrapper">
    <div data-bind="foreach: packages">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <span data-bind="text: title"
                    class="panel-title">
                </span>
                <span class="pull-right">
                    <button class="btn btn-link project-toggle">
                        <i class="fa fa-angle-down"></i>
                    </button>
                </span>
            </div>
            <div class="panel-body" style="display:none">
                <div class="row">
                    <div class="col-sm-4">
                        <a data-bind="attr: {href: ident}">
                            Link to Dryad Profile
                        </a>
                    </div>
                    <div class="col-sm-8">
                        <button data-bind="click:
                            $parent.setDOIBrowser"
                            class="btn btn-success">
                            Import Package
                        </button>
                    </div>
                </div>
                <hr/>
                <div data-bind="click:
                    $parent.clickPackage">
                    <div class="row">
                        <div class="col-sm-4">
                            <strong>Authors</strong>
                        </div>
                        <div class="col-sm-8">
                            <ul data-bind="foreach: authors">
                             <li data-bind="text: $data"></li>
                            </ul>
                        </div>
                    </div>
                    <hr/>
                    <div class="row">
                        <div class="col-sm-4">
                            <strong>Date Submitted</strong>
                        </div>
                        <div class="col-sm-8">
                            <em data-bind="text:
                                date_submitted">
                            </em>
                        </div>
                    </div>
                    <hr/>
                    <div class="row">
                        <div class="col-sm-4">
                            <strong>Date Available</strong>
                        </div>
                        <div class="col-sm-8">
                            <em data-bind="text:
                                date_available">
                            </em>
                        </div>
                    </div>
                    <hr/>
                    <div class="row">
                        <div class="col-sm-4">
                            <strong>Subjects</strong>
                        </div>
                        <div class="col-sm-8">
                            <ul data-bind="foreach: subjects">
                              <li data-bind="text: $data"></li>
                            </ul>
                        </div>
                    </div>
                    <hr/>
                    <div class="row">
                        <div class="col-sm-4">
                            <strong>Description</strong>
                        </div>
                        <div class="col-sm-8">
                            <em data-bind="text:
                                description">
                            </em>
                        </div>
                    </div>
                    <hr/>
                    <div class="row">
                        <div class="col-sm-4">
                            <strong>
                                Scientific Names
                            </strong>
                        </div>
                        <div class="col-sm-8">
                            <em data-bind="text:
                                scientific_names">
                            </em>
                        </div>
                    </div>
                    <hr/>
                    <div class="row">
                        <div class="col-sm-4">
                            <strong>Temporal Info</strong>
                        </div>
                        <div class="col-sm-8">
                            <em data-bind="text:
                                temporal_info">
                            </em>
                        </div>
                    </div>
                    <hr/>
                    <div class="row">
                        <div class="col-sm-4">
                            <strong>References</strong>
                        </div>
                        <div class="col-sm-8">
                            <em data-bind="text:
                                references">
                            </em>
                        </div>
                    </div>
                    <hr/>
                    <div class="row">
                        <div class="col-sm-4">
                            <strong>Files</strong>
                        </div>
                        <div class="col-sm-8" data-bind="foreach: files">
                            <a data-bind="text: $data, attr: {href: $data}">
                            </a>
                        </div>
                    </div>
                    <hr/>
                </div>
            </div>
        </div>
    </div><!-- end foreach: packages-->
</div><!-- end result_wrapper-->
