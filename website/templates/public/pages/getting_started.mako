<%inherit file="base.mako"/>
<%def name="title()">Getting Started</%def>
<%def name="content()">


    <div class="col-md-3 nav-list-spy">
        <ul class="nav nav-list gs-sidenav affix" id="features-nav">
            <li class="active"><a href="#start">Getting Started</a></li>
                <ul class="nav little-nav">
                    <li><a href="#start-one"><i class="icon-chevron-right"></i> Phase One</a></li>
                    <li><a href="#start-two"><i class="icon-chevron-right"></i> Phase Two</a></li>
                    <li><a href="#start-three"><i class="icon-chevron-right"></i> Phase Three</a></li>
                </ul>
            <li><a href="#features">Features</a></li>
                <ul class="nav little-nav">
                    <li><a href="#dashboards"><i class="icon-chevron-right"></i> Dashboards</a></li>
                    <li><a href="#projects"><i class="icon-chevron-right"></i> Projects</a></li>
                    <li><a href="#components"><i class="icon-chevron-right"></i> Components</a></li>
                    <li><a href="#links"><i class="icon-chevron-right"></i> Links</a></li>
                    <li><a href="#files"><i class="icon-chevron-right"></i> Files</a></li>
                    <li><a href="#privacy"><i class="icon-chevron-right"></i> Privacy</a></li>
                    <li><a href="#contributors"><i class="icon-chevron-right"></i> Contributors</a></li>
                    <li><a href="#registrations"><i class="icon-chevron-right"></i> Registrations</a></li>
                    <li><a href="#forking"><i class="icon-chevron-right"></i> Forking</a></li>
                    <li><a href="#github"><i class="icon-chevron-right"></i> GitHub</a></li>
                    <li><a href="#s3"><i class="icon-chevron-right"></i> Amazon S3</a></li>
                    <li><a href="#figshare"><i class="icon-chevron-right"></i> FigShare</a></li>
                    <li><a href="#chat"><i class="icon-chevron-right"></i> Chat</a></li>
                    <li><a href="#citations"><i class="icon-chevron-right"></i> Citations</a></li>
                </ul>
        </ul>
    </div>

    <div class="col-md-9">
        <div class="row center" style="margin-bottom: 20px;">
            <div class="headOne padded">Getting Started</div>
                <img id="start-one" class="gs-count" src="/static/img/one_big.gif">
                <p class="lead">When developing your idea, you can use the OSF to organize your background research, coordinate with potential collaborators, and pre-register hypotheses.</p>
                <div class="gs-video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/lq4LBjhbB4U" frameborder="0" allowfullscreen></iframe></div>
                <br>
                <img id="start-two" class="gs-count" src="/static/img/two_big.gif">
                <p class="lead">Keep yourself and your collaborators on point while collecting data by using the OSF. Make sure everyone has the resources they need by uploading files, connecting other services like FigShare or GitHub, and adding contributors. </p>
                <div class="gs-video"><iframe width="550" height="309"  src="//www.youtube-nocookie.com/embed/VBCaeC7eFI8" frameborder="0" allowfullscreen></iframe></div>
                <br>
                <img id="start-three" class="gs-count" src="/static/img/three_big.gif">
                <p class="lead">Share your research by making your project public and tagging it appropriately. OSF visitors will be able to cite and comment on your work, and you will be able to measure your impact using new altmetrics.</p>
                <div class="gs-video"><iframe width="550" height="309"  src="//www.youtube-nocookie.com/embed/lpHswwbX2Ek" frameborder="0" allowfullscreen></iframe></div>

        </div>
        <br><br><br><br><br><br>

        <script>
                $(document).ready(function()
                {
                    $(".gs-video").hover(
                            function()
                            {
                                var $this = $(this);
                                var $img = $this.find("img");
                                var animated = $img.data('hover-anim');
                                $img.attr("src", animated);
                            },
                            function()
                            {
                                var $this = $(this);
                                var $img = $this.find("img");
                                var still = $img.data('hover-static');
                                $img.attr("src", still);
                            }
                    );
                });
            </script>

        <p class="subHeadFour center" id="features">Getting Started With:</p>
        <div class="row " id="dashboards">
                <p class="gs-header">Dashboards</p>
                <p>Dashboards are a table of contents of your projects or project components. The user dashboard is linked in the black navigation bar at the top of the page.  This dashboard shows your public OSF profile and all of your projects--both public and private.</p>
                <div class="gs-video"><img data-hover-anim="/static/pages/getting_started/user_dashboard.gif" data-hover-static = "/static/pages/getting_started/user_dashboard.png" src="/static/pages/getting_started/user_dashboard.png"/></div>
                <p>Also, every project and component on the OSF has a dashboard of its own in the grey navigation bar below the project title.  This dashboard is an overview of the components, files, tags, history, and includes a wiki excerpt.</p>
                <div class="gs-video"><img data-hover-anim="/static/pages/getting_started/user_dashboard.gif" data-hover-static = "/static/pages/getting_started/project_dashboard.png" src="/static/pages/getting_started/project_dashboard.png"/></div>

        </div>
        <div class="row" id="projects">
                <p class="gs-header">Projects</p>
                <p>Projects are the largest form of categorization that the OSF supports. A project could be an experiment, a lab group, or a paper–anything that has contributing members and files or explanatory texts/images.</p>

        </div>
        <div class="row" id="components">
                <p class="gs-header">Components</p>
                <p>Components are like folders in your project. You can assign a component a category upon its creation (data, materials, projects, etc.). A component that is categorized as a project can have more components added within it.</p>
                <p>Components come with their own privacy settings, contributors, wikis, add-ons, and files.</p>
                <p>To delete a component or project, visit its page and go to "Settings" in the grey navigation bar under the component's title. This will also delete that component's wiki.</p>
                <div class="gs-video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/0-0W3fknETQ?rel=0" frameborder="0" allowfullscreen></iframe></div>

        </div>
        <div class="row" id="links">
                <p class="gs-header">Links</p>
                <p>Links are an alternative to building a component within a project. Adding a link to a project means that instead of building a component within the parent project, the component exists separately and is only being pointed to from the present project.</p>
                <p>Any existing public project can be pointed to.</p>
                <p>Pointing is useful if you want to reference another's work or indicate that something is part of a larger project, while still allowing it to exist independently.</p>

        </div>
        <div class="row" id="files">
                <p class="gs-header">Files</p>
                <p>Each project and component can have its own set of files. This allows you to organize your files into meaningful groups like datasets or background research.</p>
                <p>To upload a file, click on "Files" in the grey navigation bar under the Project/Component's title. Here you can drag the file from your desktop on to the screen to upload, or click on the upload button in the actions column.</p>
                <p>To download a file from a project, click the download button in the actions column.</p>
                <p>You can delete files by clicking  the ‘X’ that appears when you hover over the file.</p>
                <p>Only contributors of that component with writing privileges can add or delete a file. If a component is set to be private, then no one will be able to see the enclosed files, but public components and projects allow anyone to download their materials.</p>

                <div class="gs-video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/5qUAhUF1JL8?rel=0" frameborder="0" allowfullscreen></iframe></div>

        </div>
        <div class="row" id="privacy">
                <p class="gs-header">Privacy</p>
                <p>All projects are private by default. However, you can choose to make your project's contents available for anyone to view. </p>
                <p>Components you have added can have their own privacy settings. Making the project public does not make all of its components public. For example, you can make your methodology component public, but leave the data in a private component.</p>
                <p>Once you make a project public, you can gain more feedback about the impact of your work by tracking how many people that are visiting your projects and downloading or forking your research materials. You can also create a watchlist of other projects that interest you. </p>

        </div>
        <div class="row" id="contributors">
                <p class="gs-header">Contributors</p>
                <p>Adding contributors to a project allows credit to be given to those who have worked on the project, and allows them to make changes to the project.</p>
                <p>Admins on a project can add contributors by visiting the "Contributors" tab in the grey navigation bar under the project's name. Click on the top link labeled "Click to add a contributor." A pop-up will appear where you can search for a person to add. If they have an OSF account, their name will appear and you can add them and select their privileges. You can select what components you would like to add them to.</p>
                <p><strong>Contributor permissions</strong> are the rules that govern who can see or edit a project. When a project is made, the creator is automatically the administrator, meaning that they can add other people and make changes to the project. The admin can add contributors and make them administrators as well, or they can assign the other contributors to read or read & write priveleges.<p>
                <p>Reading privileges means that the contributor can see any project or component they are listed as a contributor on.</p>
                <p>Reading and writing privileges means that the contributor can see and edit any project or component they are a contributor on, but they cannot add or remove contributors like an administrator.</p>

                <p>Admins on a project can add contributors by visiting the "Contributors" tab in the grey navigation bar under the project's name. Click on the top link labeled "Click to add a contributor." A pop-up will appear where you can search for a person to add. If they have an OSF account, their name will appear and you can add them and select their privileges. You can select what components you would like to add them to.</p>

        </div>
        <div class="row" id="registrations">
                <p class="gs-header">Registrations</p>
                <p>Registrations are permanent, read only copies of a project. Registration saves the state of a project at a particular point in time - such as right before data collection, or right when a manuscript is submitted. To register a project, click on the button in the grey navigation bar.</p>

                <p>Click on New Registration, select a meta-data template, fill it out, and then confirm the registration.</p>

                <p>A registration exists at a separate, permanent URL that is linked to the project.  Then, you can continue editing and revising the project.</p>
                <div class="gs-video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/r0SHerHk6PY?rel=0" frameborder="0" allowfullscreen></iframe></div>

        </div>
        <div class="row" id="forking">
                <p class="gs-header">Forking</p>
                <p>Forking a project means you have created a copy of it into your dashboard, and can change that copy for your own purposes. You will be the only contributor to the forked project until you add others.</p>
                <p>Forks will automatically reference the original project as a functional citation.  Over time, the network of forks trace the evolution of project materials.</p>
                <div class="gs-video"><iframe width="550" height="309" src="//www.youtube-nocookie.com/embed/1GeAqTX51F8?rel=0" frameborder="0" allowfullscreen></iframe></div>

        </div>
        <div class="row" id="github">
                <p class="gs-header">GitHub Add-on</p>
                <p>To link a GitHub repository to a project/component, visit your profile settings by clicking the gear in the top right of the page. Check "GitHub" under "Select Add-ons" to enable the add-on.</p>
                <p>Then, authenticate with GitHub by clicking the "Create Access Token" button and following the instructions on the GitHub page. Once you have created the access token in your user profile, you will not need to follow those first few steps again. </p>
                <p>After creating the access token for your user profile, visit the project you want to add a GitHub repository to. Click on the project name then go to "Settings" in the grey navigation bar. Select the Github add-on by clicking “OK” on the pop-up, then submitting. </p>
                <p>Authorize the Github repository by clicking the blue button. Once you have authorized GitHub then you need to either select a repository or create a new one.</p>

        </div>
        <div class="row" id="s3">
                <p class="gs-header">Amazon Simple Storage Service Add-on</p>
                <p>To link Amazon Simple Storage Service bucket to a project/component, visit your profile settings by clicking the gear in the top right of the page. Check "Amazon Simple Storage Service" under "Select Add-on.”</p>
                <p>Next, authenticate Amazon Simple Storage Service by entering the access key and secret key. Then, click “Submit.”</p>
                <p>Once you have enabled Amazon Simple Storage Service in your user settings, you won’t need to do those previous steps again. To associate a bucket with a project, visit the project you want to add a Amazon Simple Storage Service bucket to. Go to "Settings" in the grey navigation bar. Select the Amazon Simple Storage Service add-on under “Select Add-ons” and click“OK” on the pop-up. Then, submit your new settings.</p>
                <p>Once you have authorized Amazon Simple Storage then you need to either select a buckets from the dropdown or create one.</p>

        </div>
        <div class="row" id="figshare">
                <p class="gs-header">FigShare Add-on</p>
                <p>Currently, the OSF only supports linking FigShare projects to an OSF project–not individual files or articles.</p>
                <p>To link a FigShare project to an OSF project, first visit your profile settings by clicking the gear in the top right of the page. Check "FigShare" under "Select Add-on.”</p>
                <p>Next, authenticate FigShare by clicking "Create Access Token" and following the instructions on the FigShare website. Once you have enabled FigShare in your user settings, you won’t need to do those previous steps again. </p>
                <p>To associate a FigShare project with an OSF project, visit the project you want to add the FigShare project to. Go to "Settings" in the grey navigation bar. Select the FigShare add-on under “Select Add-ons” and click “OK” on the pop-up. Then, submit your new settings.</p>
                <p>Still in your project settings, now click the authorize button for FigShare under "Configure Add-ons" and then select the project you want to add.</p>

        </div>
        <div class="row" id="chat">
                <p class="gs-header">Commenting</p>
                <p>Commenting can be enabled for any OSF project. To leave a comment on a project, if the administrators have allowed chat, you will see blue speech bubbles in the top right corner of your screen. Click on those speech bubbles and add your comment in the text box.</p>
                <p>You may find that you can view comments but not leave one. That is the administrator's choice, and it reflects their decision to only allow contributors to comment on the project.</p>
                <p>To change your project's comment settings, visit "Settings" in the grey navigation bar below the project title. Select your preference under "Configure Commenting" and submit your changes. </p>

        </div>
        <div class="row" id="citations">
                <p class="gs-header">Citations</p>
                <p>Every project, component, file, and user has a unique URL on the OSF. This means that anything you upload and make public on the OSF can be cited, giving you credit for your work.</p>
                <p>To find a pre-formatted citation for a project, look directly below the grey navigation bar on the project's page and you will see the URL to be cited. If you click "more" then you ill see the APA, MLA, and Chicago citations.</p>

        </div>
        <div class="empty"></div>
    </div>
    </div>
</%def>