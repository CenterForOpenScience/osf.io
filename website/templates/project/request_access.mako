<%inherit file="../base.mako"/>


<%def name="title_meta()">
    Request Access
</%def>

<%def name="content()">


<div id="requestAccessScope">
    <header class="subhead" id="overview">
        <div class="row no-gutters">
            <div class="col-lg-8 col-md-12 cite-container">
                <h2 class="node-title" style="float: left;">
                    You Need Permission
                </h2>
            </div>
            <div class="clearfix visible-md-block">
                <p data-bind="visible: !AccessRequestSuccess()">Ask for access, or switch to an account with permission.</p>
                <p data-bind="visible: AccessRequestSuccess()">Your request for access has been sent. You will receive an email if and when your request is approved.</p>

                <div>
                    <button data-bind="click: requestProjectAccess, disable: AccessRequestSuccess(), text: requestAccessButton" class="btn btn-success btn-success-high-contrast f-w-xl"></button>
                    <a type="button" href="/logout/" class="btn btn-default">Switch account</a>
                </div>
                <span id="supportMessage"></span>
            </div>
        </div>
    </header>
</div>

</%def>


<%def name="javascript_bottom()">
    <script src="${'/static/public/js/request-access-page.js' | webpack_asset}"></script>
    <script type="text/javascript">
        window.contextVars.nodeId = ${ node['id'] | sjson, n };
    </script>
</%def>