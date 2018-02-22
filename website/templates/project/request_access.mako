<%inherit file="../base.mako"/>


<%def name="title_meta()">
    Request Access
</%def>

<%def name="content()">


<div id="requestAccessPrivateScope">
    <header class="subhead" id="overview">
        <div class="row no-gutters">
            <div class="col-lg-8 col-md-12 cite-container">
                <h2 class="node-title">
                    You Need Permission
                </h2>
                <p data-bind="visible: !accessRequestPendingOrDenied()">Ask for access, or switch to an account with permission.</p>
                <p data-bind="visible: accessRequestPendingOrDenied()">Your request for access has been sent. You will receive an email if and when your request is approved.</p>
                <div>
                    <span class="request-access"
                          data-content="Request declined"
                          data-toggle="popover"
                          data-placement="top">
                    <button data-bind="click: requestProjectAccess, text: requestAccessButton, css: {disabled: accessRequestPendingOrDenied()}"
                            class="btn btn-success btn-success-high-contrast f-w-xl request-access"></button>
                    </span>
                    <a type="button" href="/logout/" class="btn btn-default">Switch account</a>
                </div>
                <div>
                    <span id="supportMessage"></span>
                </div>
            </div>
        </div>
    </header>
</div>

</%def>


<%def name="javascript_bottom()">
    <script src="${'/static/public/js/request-access-page.js' | webpack_asset}"></script>
    <script type="text/javascript">
        window.contextVars.nodeId = ${ node['id'] | sjson, n };
        window.contextVars.currentUserRequestState = ${ user['access_request_state'] | sjson, n };
    </script>
</%def>