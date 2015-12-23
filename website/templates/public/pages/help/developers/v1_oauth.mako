<%inherit file="base.mako"/>
<%def name="title()">Guide to using OAuth with the OSF</%def>

<%def name="content()">
<div class="nav-rows container">
    <div class="row">
        <div class="col-sm-4 affix-parent scrollspy col-md-3 nav-list-spy">
            <div data-spy="affix" class="hidden-print hidden-xs panel panel-default affix osf-affix m-t-lg"
                 data-offset-top="40" data-offset-bottom="268" role="complementary">
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
                <p>
                    Using the <a href="https://tools.ietf.org/html/rfc6749#section-5.2">OAuth 2.0 protocol</a>,
                    third-party applications can gain permission from a user to connect to the OSF and access
                    confidential data in the user's OSF account, without needing a password.
                </p>
                <p>
                    ## TODO: Add link (need to be in same branch as reg UI for weburlfor to work)
                    All third-party developers seeking to access private user data must first
                    <a href="">register an application</a> to obtain a client ID and client secret.
                </p>
            </div>
            <div id="quickstart" class="anchor row">
                <h2>Quickstart</h2>
                <p>
                    Below is information needed to connect via authorization code grant (also known as the web
                    application flow). This will likely be familiar to users of other OAuth implementations
                    (such as Google), and integration can be rapidly implemented using common libraries such as
                    <a href="https://requests-oauthlib.readthedocs.org/en/latest/">requests_oauthlib</a> (for Python).
                </p>
                <p>
                    ## TODO: Add link
                    In order to connect to the OSF on behalf of users, you must first <a href="">register</a> your
                    platform application and obtain a client ID/ client secret.
                </p>
                <div id="auth-grant">
                    <h3>Ask the user to grant authorization</h3>
                    <p>
                        Redirect the user to the authorization URL
                        <code>https://accounts.osf.io/oauth2/authorize</code>, as a GET request with the parameters
                        specified in the table below. Insecure requests will be refused; be sure to use HTTPS.
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
                                <td>client_id</td>
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
                                <td>scope</td>
                                <td>One or more approved values from <a href="#scopes">list</a></td>
                                <td>
                                    <p>Scopes restrict how much of the user's confidential information can be accessed
                                    by your application; users will be informed of these restrictions on the consent
                                    screen. If the application requests overly broad access, the user may choose to
                                    decline authorization. Multiple scopes from the approved <a href="#scopes">list</a>
                                    can be specified in a space-delimited, URL-encoded string (see example request),
                                    in which case the application will have permission to access all of the
                                    associated endpoints. The OSF does not support incremental authorization: all
                                    necessary scopes must be obtained when the user first authorizes access.</p>
                                    <p>If no recognized scope is specified, the authorization request will fail. There
                                    is no default scope.</p>
                                </td>
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

                    <p>An example request URL is shown below (formatted for readability):</p>
<pre>https://accounts.osf.io/oauth2/authorize?
    client_id=abcdef1234567890abcdef1234567890&
    redirect_uri=https://website.com/oauthdemo/callback/&
    approval_prompt=force&
    state=randomhash&
    scope=osf.users.all%2Bread+osf.nodes.data%2Bwrite</pre>
                    <p>
                    Successful authorization will redirect the user to the specified callback URL, with the
                    authorization grant provided in an additional URL parameter called <code>code</code>. For example:</p>
<pre>https://website.com/oauthdemo/callback/?
    code=AC-1-iNes7HZdRuAEM69pXpLXCO80cUDewzcztD7oO3GeV5PocKWhqj&
    state=FSyUOBgWiki_hyaBsa</pre>
                </div>

                <div id="access-token">
                    <h3>Exchanging authorization grant for tokens</h3>
                    <p>Send a POST request to the token grant URL <code>https://accounts.osf.io/oauth2/token</code>
                        with the parameter values described below. Insecure requests will be refused; be sure to use HTTPS.</p>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Parameter</th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>code</td>
                                <td>The authorization code received in step 1. Authorization codes expire 10 seconds after being issued.</td>
                            </tr>
                            <tr>
                                <td>client_id</td>
                                ## TODO: Add link (need to be in same branch as reg UI for weburlfor to work)
                                <td>The client ID obtained when <a href="">registering</a> the application</td>
                            </tr>
                            <tr>
                                <td>client_secret</td>
                                ## TODO: Add link (need to be in same branch as reg UI for weburlfor to work)
                                <td>The client secret obtained when <a href="">registering</a> the application</td>
                            </tr>
                            <tr>
                                <td>redirect_uri</td>
                                ## TODO: Add link
                                <td>Must exactly match the callback URL provided when <a href="">registering</a> the application.</td>
                            </tr>
                            <tr>
                                <td>grant_type</td>
                                <td>For obtaining a token, specify a value of <code>authorization_code</code>.</td>
                            </tr>
                        </tbody>
                    </table>

                    <p>A successful request will yield a response such as the one shown below:</p>
<pre>
{
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_token":"RT-1-lfBZJHbaMTUtuJs6K4xI2Ko0ZLnbMxMXkpwGRCZgJ8RNHlUQBp",
    "access_token":"AT-1-pS8mnzivmZD7O80GVsqiul683Jx5Psdqg11zynwWbEwIaVxZgSRHiCvc2yNcFqbUgrKGz1"
}
</pre>
                </div>

                <div id="refresh-token">
                    <h3>Refreshing expired tokens</h3>
                    <p>The access (bearer) token will expire after 1 hour (3600 seconds), after which time the refresh
                        token must be used to acquire a new access token. Send a POST request to the token grant
                        URL <code>https://accounts.osf.io/oauth2/token</code> with the parameter values described below.
                        Insecure requests will be refused; be sure to use HTTPS.</p>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Parameter</th>
                                <th>Values</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>refresh_token</td>
                                <td>The refresh token that was issued when the user first authorized access. This token
                                    never expires, and can be exchanged for new access tokens as needed.</td>
                            </tr>
                            <tr>
                                <td>client_id</td>
                                ## TODO: Add link (need to be in same branch as reg UI for weburlfor to work)
                                <td>The client ID obtained when <a href="">registering</a> the application</td>
                            </tr>
                            <tr>
                                <td>client_secret</td>
                                ## TODO: Add link (need to be in same branch as reg UI for weburlfor to work)
                                <td>The client secret obtained when <a href="">registering</a> the application.</td>
                            </tr>
                            <tr>
                                <td>redirect_uri</td>
                                ## TODO: Add link
                                <td>Must exactly match the callback URL provided when <a href="">registering</a> the application.</td>
                            </tr>
                            <tr>
                                <td>grant_type</td>
                                <td>Specify a value of <code>refresh_token</code>.</td>
                            </tr>
                        </tbody>
                    </table>

                    <p>A successful request will yield a response such as the one shown below.</p>
<pre>
{
    "token_type": "Bearer",
    "expires_in": 3600,
    "access_token": "AT-2-ILB6Jv7cFEeKxCnAjy7iiGo4sGaUCP8Ww84FVQPCELleY8DX3YDFtNSYb0iWe1gSofxFIV"
}
</pre>
                </div>
            </div>
            <div id="webapp-flow" class="anchor row">
                <h2>Web Application Flow</h2>
                <p>The process of acquiring access to a user's account can be broken up into a series of
                <a href="#quickstart">steps</a>. Below is a brief description of each step, of particular use to those who are
                implementing access manually, without benefit of a third-party library. For more information, see
                <a href="https://tools.ietf.org/html/rfc6749#section-1.3.1">RFC 6749</a>, the specification document for OAuth 2.0.</p>

                <ol>
                    <li>Request an authorization grant from the user: the user is directed to the authorization grant
                        URL with parameters identifying the application and type of access desired. If the user approves
                        access, the browser is redirected to the application callback URL (along with a unique, temporary
                        code that the application can exchange for access). Use of the <em>state</em> parameter is highly
                        recommended in this step as a way to discourage CSRF attacks.</li>
                    <li>Exchange the authorization code for an access token: the application callback should parse the
                        request URL to obtain the access code issued above. That code (along with a client secret known
                        only to the application owner) can be exchanged for <em>access</em> and <em>refresh</em> tokens.
                        This exchange must happen quickly- within ~10 seconds of the code being issued.</li>
                    <li>Use the access token to make a request: the access token is provided alongside every request
                        to the OSF, in a header of the form <code>Authorization: Bearer token_goes_here</code></li>
                    <li>Use the refresh token when old access tokens have expired: OSF access tokens expire after one hour.
                        The refresh token (plus client secret) can be exchanged for a new access token. Some client
                        libraries can handle this refresh process automatically. Save the refresh token; it never expires,
                        and will continue to provide access to a user's account unless the user chooses to revoke access.</li>
                </ol>
            </div>

            <div id="scopes" class="anchor row">
                <h2>Restricting Access (scopes)</h2>
                <p>
                    In order to access specific OSF features, the application authorization request must include a list of
                    <em>scopes</em>. Scopes restrict how much of the user's confidential information can be accessed
                    by your application, and users will be informed about the number and type of privileges during the
                    authorization process. If no recognized scope is provided, the authorization request will fail-
                    there is no default scope.
                </p>
                <p>
                    Although some of the scopes listed below provide combined permissions for convenience, more
                    granular access is possible by requesting multiple distinct scopes. The OSF does not support
                    incremental authorization; all necessary scopes must be obtained when the user first authorizes access.
                </p>

                <table class="table">
                    <thead>
                    <tr>
                        <td>Name</td>
                        <td>Permissions</td>
                        <td>Description</td>
                    </tr>
                    </thead>
                    <tbody>
                    <tr>
                        <td>osf.full+write</td>
                        <td>All routes (read + write)</td>
                        <td>Full access to all API endpoints, and implicitly includes all other current or future scopes.
                            Allows applications to read and modify all confidential data in the user's account,
                            including profiles and project data/visibility.</td>
                    </tr>
                    <tr>
                        <td>osf.full+read</td>
                        <td>All routes (read)</td>
                        <td>Full access to all API endpoints. Allows read-only access to all confidential data in the
                            user's account.</td>
                    </tr>
                    <tr>
                        <td>osf.users.all+write</td>
                        <td>User data (read +  write)</td>
                        <td>Allows the application to read and modify user profile data, </td>
                    </tr>
                    <tr>
                        <td>osf.users.all+read</td>
                        <td>User data (read)</td>
                        <td>Allow the application to read user profile data</td>
                    </tr>
                    <tr>
                        <td>osf.nodes.all+write</td>
                        <td>All project data (read +  write)</td>
                        <td>Read and write access to project metadata, contents, and lists of contributors/registrations.  (implicitly includes all other "osf.nodes" scopes)</td>
                    </tr>
                    <tr>
                        <td>osf.nodes.all+read</td>
                        <td>All project data (read +  write)</td>
                        <td>Read-only access to project metadata, contents, and lists of contributors/registrations.  (implicitly includes all other "osf.nodes" scopes)</td>
                    </tr>
                    <tr>
                        <td>osf.nodes.metadata+write</td>
                        <td>Project metadata (read +  write)</td>
                        <td>Access a list of all public and private projects. View and edit project metadata, such as titles and descriptions. Also grants the ability to create and delete projects.</td>
                    </tr>
                    <tr>
                        <td>osf.nodes.metadata+read</td>
                        <td>Project metadata (read)</td>
                        <td>Access a list of all public and private projects. View project metadata, such as titles and descriptions.</td>
                    </tr>
                    <tr>
                        <td>osf.nodes.data+write</td>
                        <td>Project content (read + write)</td>
                        ## TODO: Are wiki content endpoints planned? Any data other than files?
                        <td>Access project contents, such as files and wiki pages. Modify and delete files.</td>
                    </tr>
                    <tr>
                        <td>osf.nodes.data+read</td>
                        ## TODO Currently files endpoint provides enough info to write and edit files
                        <td>Project content (read + write)</td>
                        <td></td>
                    </tr>
                    <tr>
                        <td>osf.nodes.access+write</td>
                        <td>Control access to projects (read + write)</td>
                        ## TODO: Will API endpoints allow us to make certain projects public?
                        <td>View a list of contributors for all public and private projects. List and create project
                        registrations, and change the privacy settings on projects.</td>
                    </tr>
                    <tr>
                        <td>osf.nodes.access+read</td>
                        <td>See who has access to projects (read)</td>
                        <td>View list of project contributors and registrations.</td>
                    </tr>
                    </tbody>
                </table>
            </div>
            <div id="common-errors" class="anchor row">
                <h2>Common Errors</h2>
                If there are problems with the authorization grant request, the user will be redirected to the
                registered callback URL with an added <code>error</code> parameter describing the failure reason.

                ## TODO: Expand list based on @icereval's pending CAS changes.
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
            </div>
            <div id="tips" class="anchor row">
                <h2>Helpful tips</h2>
                ## TODO: Should we be publicizing the testing server externally?
                <p>We provide a <a href="https://staging.osf.io">staging server</a> that can be used for application testing purposes.
                Note that this server may behave slightly differently than the production environment, with new or modified features, or minor bugs.
                The OAuth 2.0 <a href="#quickstart">base URL</a> for the staging server is <code>https://staging-accounts.osf.io/</code>.</p>
            </div>
        </div>
    </div>
</div>

</%def>
