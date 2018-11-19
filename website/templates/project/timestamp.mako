<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Timestamp</%def>

<div class="page-header  visible-xs">
  <h2 class="text-300">Timestamp</h2>
</div>

<div class="row">
    <div class="col-sm-5">
        <h2 class="break-word">
            Timestamp Control
        </h2>
    </div>
    <div class="col-sm-7">
        <div id="toggleBar" class="pull-right"></div>
    </div>
</div>
<hr/>
<div class="row project-page">

    <!-- Begin left column -->
    <div class="col-md-3 col-xs-12 affix-parent scrollspy">
        <div class="panel panel-default osf-affix" data-spy="affix" data-offset-top="0" data-offset-bottom="263">
            <!-- Begin sidebar -->
            <ul class="nav nav-stacked nav-pills">
                <li class="active"><a href="#">Timestamp Error</a></li>
            </ul>
        </div>
    </div>

    <div class="col-md-9 col-xs-12">
        <form id="timestamp-form" class="form">
            <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
                <span>
                    <button type="button" class="btn btn-success" id="btn-verify">Verify</button>
                    <button type="button" class="btn btn-success" id="btn-addtimestamp">Request Trusted Timestamp</button>
                </span>
            </div>
            <span id="configureNodeAnchor" class="anchor"></span>
            <table class="table table-bordered table-addon-terms">
                <thead class="block-head">
                    <tr>
                        <th width="3%"><input type="checkBox" id="addTimestampAllCheck" style="width: 15px; height: 15px;"/></th>
                        <th width="40%">File Path</th>
                        <th width="15%">Timestamp Update User</th>
                        <th width="22%">Timestamp Update Date</th>
                        <th widht="20%">Timestamp Verification</th>
                    </tr>
                </thead>
                <font color="red">
                    <div id="timestamp_errors_spinner" class="spinner-loading-wrapper">
                        <div class="logo-spin logo-lg"></div>
                        <p class="m-t-sm fg-load-message"> Loading timestamp error list ...  </p>
                    </div>
                </font>
                <tbody id="timestamp_error_list">
                </tbody>
            </table>
        </form>
    </div>
</div>

<style type="text/css">
    .table>thead>tr>th {
        vertical-align: middle;
    }
</style>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    % for script in tree_js:
        <script type="text/javascript" src="${script | webpack_asset}"></script>
    % endfor
    <script>
        window.contextVars.project_file_list = window.contextVars.project_file_list || {};
        window.contextVars.project_file_list = ${provider_list| sjson, n }
    </script>

    <script src=${"/static/public/js/timestamp-page.js" | webpack_asset}></script>
</%def>
