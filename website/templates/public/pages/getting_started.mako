<%inherit file="base.mako"/>
<%def name="title()">Getting Started</%def>
<%def name="content()">

<style>
    .video {
        margin-top: 25px;
        margin-bottom: 25px;
        margin-left: 100px;
    }

    .row {
        margin-top: 40px;
        margin-bottom: 40px;
    }
</style>

<h1 class="page-title" style="text-align:center">Getting Started</h1>
            <h2 style="text-align: center; margin-bottom: 20px;">The Research Lifecycle</h2>
<div class="container">
    <div class="row" style="margin-bottom: 20px;">
        <div class="col-md-12">

            </div>
        <div class="col-md-8 col-md-offset-2">
            <p>The OSF supports you during any phase of your research. Watch the videos below to see how OSF features can facilitate initial idea generation and organization, developing a project and preserving data, and publicizing your work.</p>
        </div>
    </div>
    <div class="row">
        <div class="col-md-4">
            <div><iframe width="325" height="183" src="//www.youtube-nocookie.com/embed/lq4LBjhbB4U" frameborder="0" allowfullscreen></iframe></div>
        </div>
        <div class="col-md-4">
            <div><iframe width="325" height="183" src="//www.youtube-nocookie.com/embed/VBCaeC7eFI8" frameborder="0" allowfullscreen></iframe></div>
        </div>
        <div class="col-md-4">
            <div><iframe width="325" height="183" src="//www.youtube-nocookie.com/embed/lpHswwbX2Ek" frameborder="0" allowfullscreen></iframe></div>
        </div>
    </div>
</div>
            <h2 style="text-align: center; margin-top: 80px;">Features</h2>
<div class="container">
    <div class="row" style="margin-top: 0px;">
        <div class="col-md-8 col-md-offset-2">
            <h3>Dashboards</h3>
            <p>Dashboards are a table of contents of your projects or project components. The user dashboard is linked in the black navigation bar at the top of the page.  This dashboard shows your public OSF profile and all of your projects--both public and private.</p>

            <div class="video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/evu2Sf44CWk?rel=0" frameborder="0" allowfullscreen></iframe></div>
            <p>Also, every project and component on the OSF has a dashboard of its own in the grey navigation bar below the project title.  This dashboard is an overview of the components, files, tags, history, and includes a wiki excerpt.</p>
            <div class="video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/OjFT8nEajJE?rel=0" frameborder="0" allowfullscreen></iframe></div>
        </div>
    </div>
    <div class="row">
        <div class="col-md-8 col-md-offset-2">
            <h3>Components and Privacy</h3>
            <p>Components are like folders in your project. You can assign a component a category upon its creation (data, materials, projects, etc.). A component that is categorized as a project can have more components added within it.</p>
             <div class="video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/sg4lcI_d5ao?rel=0" frameborder="0" allowfullscreen></iframe></div>

            <p>To delete a component or project, visit its page and go to "Settings" in the grey navigation bar under the component's title. This will also delete that component's wiki.</p>
            <div class="video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/0-0W3fknETQ?rel=0" frameborder="0" allowfullscreen></iframe></div>
            <h4>Privacy</h4>
            <p>All projects are private by default. However, you can choose to make your project's contents available for anyone to view. </p>
            <p>Components you have added can have their own privacy settings. So, making the project public does not make all of its components public. For example, you can make your methodology component public, but leave the data in a private component.</p>
            <p>Once you make a project public, you can gain more feedback about the impact of your work by tracking how many people that are visiting your projects and downloading or forking your research materials. You can also create a watchlist on other projects that interest you. </p>
        </div>
    </div>
    <div class="row">
        <div class="col-md-8 col-md-offset-2">
            <h3>Files</h3>
            <p>Each project and component can have its own set of files. This allows you to organize your files into meaningful groups like datasets or background research.</p>
            <p>To upload a file, click on "Files" in the grey navigation bar under the Project/Component's title. Here you can drag the file from your desktop on to the screen to upload, or click on the upload button in the actions column.</p>
            <p>To download a file from a project, click the download button in the actions column.</p>
            <p>You can delete files by clicking  the ‘X’ that appears when you hover over the file.</p>
            <p>Only contributors of that component can add or delete a file. If a component is set to be private, then no one will be able to see the enclosed files, but public components and projects allow anyone to download their materials.</p>

            <div class="video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/5qUAhUF1JL8?rel=0" frameborder="0" allowfullscreen></iframe></div>
        </div>
    </div>
    <div class="row" id="github">
        <div class="col-md-8 col-md-offset-2">
            <h3>GitHub Add-on</h3>
            <p>To link a GitHub repository to a project/component, visit your profile settings by clicking the gear in the top right of the page. Check "GitHub" under "Select Add-ons" to enable the add-on.</p>
            <p>Then, authenticate with GitHub by clicking the "Create Access Token" button and following the instructions on the GitHub page. Once you have created the access token in your user profile, you will not need to follow those first few steps again. </p>
            <p>After creating the access token for your user profile, visit the project you want to add a GitHub repository to. Click on the project name then go to "Settings" in the grey navigation bar. Select the Github add-on by clicking “OK” on the pop-up, then submitting. </p>
            <p>Authorize the Github repository by clicking the blue button. Once you have authorized GitHub then you need to either select a repository or create a new one.</p>
        </div>
    </div>
    <div class="row" id="s3">
        <div class="col-md-8 col-md-offset-2">
            <h3>Amazon Simple Storage Service Add-on</h3>
            <p>To link Amazon Simple Storage Service bucket to a project/component, visit your profile settings by clicking the gear in the top right of the page. Check "Amazon Simple Storage Service" under "Select Add-on.”</p>
            <p>Next, authenticate Amazon Simple Storage Service by entering the access key and secret key. Then, click “Submit.”</p>
            <p>Once you have enabled Amazon Simple Storage Service in your user settings, you won’t need to do those previous steps again. To associate a bucket with a project, visit the project you want to add a Amazon Simple Storage Service bucket to. Go to "Settings" in the grey navigation bar. Select the Amazon Simple Storage Service add-on under “Select Add-ons” and click“OK” on the pop-up. Then, submit your new settings.</p>
            <p>Once you have authorized Amazon Simple Storage then you need to either select a buckets from the dropdown or create one.</p>
        </div>
    </div>
    <div class="row">
         <div class="col-md-8 col-md-offset-2">
            <h3>Contributors</h3>
            <p>Adding contributors to a project means that they can access the project even if it is private, and add and edit the project.</p>

            <p>Add a contributor by entering their name in the field under the project title. If they have an OSF account, there name will appear and you can add them. You can select what components you would like to add them to.</p>
             <div class="video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/X6dG95ZiSYo?rel=0" frameborder="0" allowfullscreen></iframe></div>
        </div>
    </div>
    <div class="row">
        <div class="col-md-8 col-md-offset-2">
            <h3>Registrations</h3>
            <p>Registrations are permanent, read only copies of a project. Registration saves the state of a project at a particular point in time - such as right before data collection, or right when a manuscript is submitted. To register a project, click on the button in the grey navigation bar.</p>

            <p>Click on New Registration, select a meta-data template, fill it out, and then confirm the registration.</p>

            <p>A registration exists at a separate, permanent URL that is linked to the project.  Then, you can continue editing and revising the project.</p>
            <div class="video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/r0SHerHk6PY?rel=0" frameborder="0" allowfullscreen></iframe></div>
        </div>
    </div>
    <div class="row">
        <div class="col-md-8 col-md-offset-2">
            <h3>Forking</h3>
            <p>Forking a project means you have created a copy of it into your dashboard, and can change that copy for your own purposes. You will be the only contributor to the forked project until you add others.</p>

            <p>Forks will automatically reference the original project as a functional citation.  Over time, the network of forks trace the evolution of project materials.</p>
            <div class="video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/1GeAqTX51F8?rel=0" frameborder="0" allowfullscreen></iframe></div>
        </div>
    </div>
</div>

</%def>