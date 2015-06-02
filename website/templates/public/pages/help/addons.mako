<p>The OSF makes integrating your various research tools easy. We are always developing Add-On connections to services
    you already use. An add-on is a connection between the OSF to another, existing tool.</p>
<p>Some Add-Ons can be added to the entire user account, like Two-Factor Authentication. To access these, navigate to
    your user settings using the gear in the top right corner. Then select "Configure Add-Ons". Here you can choose
    which Add-Ons to apply.</p>
<p>Other Add-Ons only apply to individual projects. Our storage options are one example of this. They can
    only be accessed and applied from your project's settings. </p>
<p>Most Add-Ons require both account authentication as well as project application. The easiest way to do this is
    directly from the project page. First, navigate to the project's settings. Then select the Add-Ons that you want to
    incorporate into your project. A pop-up with information about the Add-On will show up, click okay, and then click
    submit. After clicking submit, you will notice a box labled "Configure Add-Ons" beneath the "Select Add-Ons" box.
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
    <h3 class="text-center" style="padding-top: 20px;">Storage Options</h3>
    <div class=" col-md-12">
        <%include file="/public/pages/help/addons/dropbox.mako"/>
        <%include file="/public/pages/help/addons/github.mako"/>
        <%include file="/public/pages/help/addons/amazons3.mako"/>
        <%include file="/public/pages/help/addons/figshare.mako"/>
        <%include file="/public/pages/help/addons/dataverse.mako"/>
        <%include file="/public/pages/help/addons/box.mako"/>
        <%include file="/public/pages/help/addons/drive.mako"/>

    <h3 class= "text-center" style="padding-top: 20px;">Citation Managers</h3>
        <%include file="/public/pages/help/addons/mendeley.mako"/>
        <%include file="/public/pages/help/addons/zotero.mako"/>

    <h3 class="text-center" style="padding-top: 20px;">Security</h3>
        <%include file="/public/pages/help/addons/two-factor.mako"/>
    </div>
</div>