<%inherit file="base.mako"/>
<%def name="title()">Spam Admin</%def>
<%def name="content()">
<div id="spam-admin" class="scripted">
    <nav class="navbar navbar-default">
        <div class="container-fluid">
            <div class="navbar-header">
                <a class="navbar-brand" href="#">Comments
                    <span class="badge" data-bind="text: total"></span>
                </a>
            </div><!-- /.navbar-header -->
            <div class="collapse navbar-collapse" >
                <ul class="nav navbar-nav">
                    <li class="active">
                        <a href="/spam_admin/comments">Comments
                            <span class="sr-only">(current)</span>
                        </a>
                    </li>
                    <li >
                        <a href="/spam_admin/projects">Projects</a>
                    </li>
                </ul>
            </div><!-- /.navbar-collapse -->
        </div><!-- /.container-fluid -->
    </nav>
    <div  data-bind="foreach: {data: spamAdminComments, as: 'comment'}">
        <div class="search-result well">
            <div class="pull-right"  role="group" aria-label="...">
                <button type="button" class="btn btn-success" data-bind="click: function(data, event) { $parent.markHam(data, event) }" >Ham</button>
                <button type="button" class="btn btn-danger" data-bind="click: function(data, event) { $parent.markSpam(data, event) }">Spam</button>
            </div><!-- /.pull-right -->
            <h4>
                <a data-bind="attr: { href: comment.project_url }" >
                    <span data-bind="text: comment.project"></span>
                </a>
            </h4>
            <p>
                <span data-bind="text: comment.content"></span>
            </p>
            <p>
                <strong>Author:</strong>
                <span data-bind="text: comment.author"></span>
                <span class="pull-right">
                    <strong>Last Edited:</strong>
                    <span data-bind="text: comment.dateModified"></span>
                </span>
            </p>
        </div><!-- /.search-result well -->
    </div><!-- /.foreach comments -->
</div><!-- /.scripted -->
</%def>
<%def name="javascript_bottom()">
    <script src=${"/static/public/js/spam-admin-comment-page.js" | webpack_asset}></script>
</%def>