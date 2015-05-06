<%inherit file="base.mako"/>
<%def name="title()">Spam Admin</%def>
<%def name="content()">


<div id="spam-admin" class="scripted">

    <nav class="navbar navbar-default">
  <div class="container-fluid">
    <!-- Brand and toggle get grouped for better mobile display -->
    <div class="navbar-header">
      <a class="navbar-brand" href="#">Projects <span class="badge" data-bind="text: total"></span></a>
    </div>


    <div class="collapse navbar-collapse" >
      <ul class="nav navbar-nav">
        <li ><a href="/spam_admin/comments">Comments </a></li>
        <li class="active"><a href="/spam_admin/projects">Projects <span class="sr-only">(current)</span></a></li>

      </ul>


    </div><!-- /.navbar-collapse -->
  </div><!-- /.container-fluid -->
</nav>


        <div  data-bind="foreach: {data: spamAdminProjects, as: 'project'}">
            <div class="search-result well">
                <div class=" pull-right"  role="group" aria-label="...">
                    <button type="button" class="btn btn-success" data-bind="click: function(data, event) { $parent.markHam(data, event) }" >Ham</button>
                    <button type="button" class="btn btn-danger" data-bind="click: function(data, event) { $parent.markSpam(data, event) }">Spam</button>
                </div>
                <h4>
                    <a data-bind="attr: { href: project.url }" >
                        <span data-bind="text: project.title"></span>
                    </a>
                </h4>
                <p>
                    <span class="small" data-bind="text: project.description"></span>
                </p>

                <div data-bind="foreach: {data: project.wikis, as: 'wiki'}">
                    <div class="panel panel-default">
                      <div class="panel-heading">
                          <a data-bind="attr: {href: wiki.url}"><span data-bind="text: wiki.page_name"></span></a>
                          <span data-bind="text: wiki.date" class="pull-right"></span>
                      </div>
                      <div class="panel-body" >
                        <span data-bind="text: wiki.content"></span>
                      </div>
                    </div>
                </div>


                <div data-bind="foreach: {data: project.tags, as: 'tag'}">

                 <span class="label label-success" data-bind="text: $data">Default</span>

                </div>


                <div class="panel panel-default">
                  <!-- Default panel contents -->
                  <div class="panel-heading">Components</div>

                  <!-- List group -->
                  <ul class="list-group">
                      <!-- ko foreach: project.components -->
                        <li class="list-group-item">
                            <a data-bind="attr: {href: url}">
                                <span data-bind="text: title"></span>
                            </a>

                            <span class="pull-right" data-bind="text: date_modified"></span>
                        </li>
                    <!-- /ko -->

                  </ul>
                </div>








                <p>
                    <strong>Author:</strong>
                    <span data-bind="text: project.author"></span>
                    <span class="pull-right">
                        <strong>Last Edited:</strong>
                        <span data-bind="text: project.dateModified"></span>
                    </span>
                </p>
            </div>
        </div>








</%def>



<%def name="javascript_bottom()">
<script src=${"/static/public/js/spam-admin-project-page.js" | webpack_asset}></script>
</%def>