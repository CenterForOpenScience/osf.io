<p>An add-on is a connection between the OSF to another tool such as Google Drive or GitHub.</p>

<p>You can connect an add-on from a project's "Settings" page.  Select the add-on to connect to your project.
    In the "Configure Add-ons" section of the page, click "Connect Account" and log in to the third-party service,
    if necessary. Once connected, you will be sent back to the "Settings" page, where you can choose what
    you want to share.</p>


<div class="row">
    <div class="col-md-12">
        <div class="col-md-12">
            <h3 class="text-center m-t-xl f-w-lg">Storage options</h3>
        </div>
        <%include file="/public/pages/help/addons/dropbox.mako"/>
        <%include file="/public/pages/help/addons/github.mako"/>
        <%include file="/public/pages/help/addons/amazons3.mako"/>
        <%include file="/public/pages/help/addons/figshare.mako"/>
        <%include file="/public/pages/help/addons/dataverse.mako"/>
        <%include file="/public/pages/help/addons/box.mako"/>
        <%include file="/public/pages/help/addons/drive.mako"/>

        <div class="col-md-12">
            <h3 class= "text-center m-t-xl f-w-lg">Citation managers</h3>
        </div>
        <%include file="/public/pages/help/addons/mendeley.mako"/>
        <%include file="/public/pages/help/addons/zotero.mako"/>

        <div class="col-md-12">
            <h3 class="text-center m-t-xl f-w-lg" >Security</h3>
        </div>
        <%include file="/public/pages/help/addons/two-factor.mako"/>
    </div>
</div>
