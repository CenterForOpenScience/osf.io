<p>The OSF makes integrating your various research tools easy. We are always developing Add-On connections to services
    you already use. An add-on is a connection between the OSF to another, existing tool.</p>
<p>To connect an add-on to a project, you can do this through your project's Settings page. Should you ever want to remove
    an add-on from all of its connected projects, you can visit your account settings page by clicking on the gear in the 
    top navigation bar. Then, click on "Configure Add-on Accounts." You can disconnect an account that has been enabled by scrolling
    to that add-on and clicking "Disconnect Account." If you want to associate your OSF account with an add-on but do 
    not yet have a specific project to link it to, you can do so from the same page by clicking "Connect Account."</p>
<p>Most Add-Ons require both account authentication as well as project application. The easiest way to do this is
    directly from the project page. First, navigate to the project's settings. Then select the Add-Ons that you want to
    incorporate into your project. A pop-up with information about the Add-On will show up, click okay, and then click
    submit. After clicking submit, you will notice a box labeled "Configure Add-Ons" beneath the "Select Add-Ons" box.
    Go to the "Configure Add-Ons" box and create an access token for the Add-On, this authorizes the Add-On for the
    entire OSF account. Then configure the Add-On and click submit to apply the Add-On to the individual project.
    Once you've authorized an Add-On, you never have to do it again. However, you always need to apply the Add-On to
    your individual projects. </p>

<div class="row">
    <div class="col-md-offset-2 col-md-8">
        <div class="gs-video embed-responsive embed-responsive-16by9">
            <div class="embed-responsive-item youtube-loader" id="h1hJkm2FE7U"></div>
        </div>
    </div>
</div>


<div class="row">
    <div class="col-md-12">
        <div class="col-md-12">
            <h3 class="text-center m-t-xl f-w-lg">Storage Options</h3>
        </div>
        <%include file="/public/pages/help/addons/dropbox.mako"/>
        <%include file="/public/pages/help/addons/github.mako"/>
        <%include file="/public/pages/help/addons/amazons3.mako"/>
        <%include file="/public/pages/help/addons/figshare.mako"/>
        <%include file="/public/pages/help/addons/dataverse.mako"/>
        <%include file="/public/pages/help/addons/box.mako"/>
        <%include file="/public/pages/help/addons/drive.mako"/>

        <div class="col-md-12">
            <h3 class= "text-center m-t-xl f-w-lg">Citation Managers</h3>
        </div>
        <%include file="/public/pages/help/addons/mendeley.mako"/>
        <%include file="/public/pages/help/addons/zotero.mako"/>

        <div class="col-md-12">
            <h3 class="text-center m-t-xl f-w-lg" >Security</h3>
        </div>
        <%include file="/public/pages/help/addons/two-factor.mako"/>
    </div>
</div>
