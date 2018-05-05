<%inherit file="base.mako"/>
<%def name="title()">Request Access</%def>
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

                    <button class="btn btn-success btn-success-high-contrast f-w-xl request-access"
                            data-bind="click: requestProjectAccess,
                                       text: requestAccessButton,
                                       css: {'disabled': accessRequestPendingOrDenied()},
                                       tooltip: {title: accessRequestTooltip(),'disabled': true, 'placement': 'top'}">
                    </button>
                    <a type="button" class="btn btn-default" href="${web_url_for('auth_logout', next=node['url'])}" >Switch account</a>
                </div>
                <div>
                    <p style="margin-top: 10px;" data-bind="html: supportMessage"></p>
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