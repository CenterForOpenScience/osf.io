<%inherit file="base.mako"/>
<%def name="title()">Guide to using OAuth with the OSF</%def>

<%def name="content()">
<div class="nav-rows container">
    <div class="row">
        <div class="col-sm-4 affix-parent scrollspy col-md-3 nav-list-spy">
            <div data-spy="affix" class="hidden-print hidden-xs panel panel-default affix osf-affix m-t-lg" data-offset-top="40" data-offset-bottom="268" role="complementary">
                <ul class="nav nav-stacked nav-pills" style="min-width: 210px">
                    <li><a class="active" href="#introduction">Introduction</a></li>
                    <li><a class="active" href="#quickstart">Quickstart</a></li>
                    <li><a href="#webapp-flow">Web Application Flow</a></li>
                    <li><a href="#scopes">Restricting Access (scopes)</a></li>
                    <li><a href="#common-errors">Common Errors</a></li>
                    <li><a href="#tips">Helpful tips</a></li>
                </ul>
            </div>
        </div>

        <div class="col-sm-8 col-md-9 p-l-md">

            <h1>Connecting to the OSF</h1>

            <div id="introduction" class="anchor row">
                <h2>Introduction</h2>
                The OSF allows third-party web applications to connect to the OSF on behalf of other users, via
                the OAuth 2.0 web application flow. This document describes the process of obtaining access tokens
            </div>
            <div id="quickstart" class="anchor row">
                <h2>Quickstart</h2>
                <p>
                    The OSF implements the OAuth 2.0 framework via the authorization code grant (web application)
                    flow. The procedures for connecting are therefore familiar for those who have used other OAuth implementations (such as Google),
                    and integration can be rapidly implemented using common libraries such as
                    <a href="https://requests-oauthlib.readthedocs.org/en/latest/">requests_oauthlib</a> (for Python).
                </p>
                <p>
                    ## TODO: Add link
                    In order to connect to the OSF on behalf of users, you must first <a href="">register</a> your platform application and obtain a client ID/ client secret.
                </p>
                <div id="auth-grant">
                    <h3>Ask the user to grant authorization</h3>
                    <p>
                        In order to request authorization, send a GET request with parameters added to the authorization URL
                        <code>https://accounts.osf.io/oauth2/authorize</code> as specified in the table below.
                        Insecure requests will be refused; be sure to use HTTPS.
                    </p>

                    <table class="table">
                        <thead>
                            <tr>
                                <th>Parameter</th>
                                <th>Values</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>client id</td>
                                ## TODO: Add link (need to be in same branch as reg UI for weburlfor to work)
                                <td>The client ID obtained when <a href="">registering</a> the application</td>
                                <td>
                                    Each application requesting access to the OSF on behalf of a user must register for a unique Client ID.
                                    The value here must exactly match the client ID given in the application detail page for the registered Developer App.
                                </td>
                            </tr>
                            <tr>
                                <td>redirect_uri</td>
                                ## TODO: Add link
                                <td>The callback URL provided when <a href="">registering</a> the application.</td>
                                <td>Where to redirect the user in order to respond after an authorization request.
                                    Must exactly match the callback URL provided when registering the application.</td>
                            </tr>
                            <tr>
                                <td>approval_prompt</td>
                                <td><code>auto</code> (default) or <code>force</code></td>
                                <td>
                                    Whether to show an approval prompt even if the user has previously authorized the
                                    application. The default is <code>auto</code>, meaning that the user will not see an
                                    authorization screen if the application already has permission.
                                </td>
                            </tr>
                            <tr>
                                <td>state</td>
                                <td>Any string</td>
                                <td>This value will be returned unchanged along with the authorization grant code. Use
                                    of this field is highly recommended as a means to provide cross-site request forgery
                                    (CSRF) tokens; the application owner should confirm the state in the callback.</td>
                            </tr>
                        </tbody>
                    </table>

                    <p>An example URL is shown below (formatted for readability):</p>
<pre>https://accounts.osf.io/oauth2/authorize?
    client_id=abcdef1234567890abcdef1234567890&
    redirect_uri=https://website.com/oauthdemo/callback/&
    approval_prompt=force&
    state=randomhash</pre>
                    Successful authorization will redirect the user to the specified callback URL, with the
                    authorization grant provided in an additional URL parameter called <code>code</code>.
                </div>

                <div id="access-token">
                    <h3>Exchanging authorization grant for tokens</h3>
                    <p>Send a POST request to the token grant URL <code>https://accounts.osf.io/oauth2/token</code>
                        with the parameter values described below.</p>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Parameter</th>
                                <th>Values</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>code</td>
                                <td>The authorization code received in step 1</td>
                                <td>An authorization code previously issued on behalf of the user, which can be
                                    exchanged for access and refresh token. This must be done quickly, as authorization codes
                                    expire 10 seconds after being issued.</td>
                            </tr>
                            <tr>
                                <td>client id</td>
                                ## TODO: Add link (need to be in same branch as reg UI for weburlfor to work)
                                <td>The client ID obtained when <a href="">registering</a> the application</td>
                                <td>
                                    Each application requesting access to the OSF on behalf of a user must register for a unique Client ID.
                                    The value here must exactly match the client ID given in the application detail page for the registered Developer App.
                                </td>
                            </tr>
                            <tr>
                                <td>client secret</td>
                                ## TODO: Add link (need to be in same branch as reg UI for weburlfor to work)
                                <td>The client secret obtained when <a href="">registering</a> the application</td>
                                <td>
                                    Each application requesting access to the OSF on behalf of a user must register in advance.
                                    The value of client secret should remain secret (known only to the application owner),
                                    and must exactly match the client secret given in the application detail page for the registered Developer App.
                                </td>
                            </tr>
                            <tr>
                                <td>redirect_uri</td>
                                ## TODO: Add link
                                <td>The callback URL provided when <a href="">registering</a> the application.</td>
                                <td>Where to redirect the user in order to respond after an authorization request.
                                    Must exactly match the callback URL provided when registering the application.</td>
                            </tr>
                            <tr>
                                <td>grant_type</td>
                                <td><code>authorization_code</code></td>
                                <td>For obtaining a token, specify a value of <code>authorization_code</code>.</td>
                            </tr>
                        </tbody>
                    </table>

                    <p>A successful request will yield a response such as the one shown below:</p>
<pre>
{
    "token_type":"bearer",
    "expires_in":3597,
    "refresh_token":"TGT-1-a3ZMZfRtMqOWSQA5kNNxvGAOkA1lGKoB0KNz0M3mola09BzU3W-accounts.osf.io",
    "access_token":"ST-11-EiHKg0IqWvvC1MN0O50A-accounts.osf.io"
}
</pre>
                </div>

                <div id="refresh-token">
                    <h3>Refreshing expired tokens</h3>
                    <p>The access (bearer) token will expire after 1 hour (3600 seconds), after which time the refresh
                        token must be used to acquire a new access token. </p>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Parameter</th>
                                <th>Values</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td></td>
                                <td></td>
                                <td></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <div id="webapp-flow" class="anchor row">
                <h2>Web Application Flow</h2>
                <p>The process of acquiring access to a user's account can be broken up into a series of
                <a href="#quickstart">steps</a>. Below is a brief description of each step, of particular use to those who are
                implementing access manually, without benefit of a third-party library. For more information, see
                <a href="https://tools.ietf.org/html/rfc6749#section-1.3.1">RFC 6749</a>, the specification document for OAuth 2.0.</p>

                <ol>
                    <li>Request an authorization grant from the user</li>
                    <li>Exchange the authorization grant for an access token</li>
                    <li>Use the access token to make a request</li>
                    <li>Use the refresh token when old access tokens have expired</li>
                </ol>

            </div>

            <div id="scopes" class="anchor row">
                <h2>Restricting Access (scopes)</h2>
                At present, all OAuth 2.0 tokens issued on behalf of a user will provide full access to that user's account.
                In the future, we will provide a set of scopes that allow users to grant limited, incremental permissions to a third party.
                All non-scoped requests should be considered a temporary implementation.
                ## TODO: Review above statement. How do we want to handle migration/ backwards compatibility?
            </div>
            <div id="common-errors" class="anchor row">
                <h2>Common Errors</h2>
                If there are problems with the authorization grant request, the user will be redirected to the
                registered callback URL with an added <code>error</code> parameter describing the failure reason.

                <table class="table">
                    <thead>
                        <tr>
                            <th>Error name</th>
                            <th>Error description</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>access_denied</td>
                            <td>The user has clicked the "deny" button, refusing to grant access to their account.
                                If the user denies access via other means (such as closing the browser window),
                                the application owner may never see this message at all.</td>
                        </tr>
                    </tbody>
                </table>
                ## TODO: Expand list based on @icereval's pending CAS changes.
            </div>
            <div id="tips" class="anchor row">
                <h2>Helpful tips</h2>
                ## TODO: Should we promote the testing server externally?
                <p>We provide a <a href="https://staging.osf.io">staging server</a> that can be used for application testing purposes, to avoid making
                Note that this server may behave slightly differently than the production environment, with new or modified features, or bugs that have not yet been fixed.
                The OAuth 2.0 authorization grant request <a href="#quickstart">base URL</a> for the staging server is <code>https://staging-accounts.osf.io/</code>.</p>
            </div>
        </div>
    </div>
</div>

</%def>
