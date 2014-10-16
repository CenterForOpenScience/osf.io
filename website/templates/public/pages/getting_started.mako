<%inherit file="base.mako"/>
<%def name="title()">Getting Started</%def>
<%def name="content()">
    <div class='row'>
        <div class="col-md-3 nav-list-spy">
            <div class="gs-sidebar hidden-print hidden-xs hidden-sm" role="complementary">
                <ul data-spy="affix" data-offset-top="0" data-offset-bottom="270" class="nav gs-sidenav">
                    <li>
                        <a href="#start">Getting Started</a>
                        <ul class="nav">
                            <li><a href="#start-one"><i class="icon-chevron-right"></i> Phase One</a></li>
                            <li><a href="#start-two"><i class="icon-chevron-right"></i> Phase Two</a></li>
                            <li><a href="#start-three"><i class="icon-chevron-right"></i> Phase Three</a></li>
                        </ul>
                    </li>
                    <li>
                        <a href="#structure">Structure</a>
                        <ul class="nav">
                            <li><a href="#dashboards"><i class="icon-chevron-right"></i> Dashboard</a></li>
                            <li><a href="#projects"><i class="icon-chevron-right"></i> Projects</a></li>
                            <li><a href="#components"><i class="icon-chevron-right"></i> Components</a></li>
                            <li><a href="#files"><i class="icon-chevron-right"></i> Files</a></li>
                            <li><a href="#links"><i class="icon-chevron-right"></i> Links</a></li>
                            <li><a href="#forks"><i class="icon-chevron-right"></i> Forks</a></li>
                            <li><a href="#registrations"><i class="icon-chevron-right"></i> Registrations</a></li>
                            <li><a href="#organizer"><i class="icon-chevron-right"></i> Project Organizer</a></li>
                        </ul>
                    </li>
                    <li>
                        <a href="#sharing">Sharing</a>
                        <ul class="nav">
                            <li><a href="#contributors"><i class="icon-chevron-right"></i> Contributors</a></li>
                            <li><a href="#privacy"><i class="icon-chevron-right"></i> Privacy</a></li>
                            <li><a href="#viewonly"><i class="icon-chevron-right"></i> View-only Links</a></li>
                            <li><a href="#comments"><i class="icon-chevron-right"></i> Comments</a></li>
                        </ul>
                    </li>
                    <li>
                        <a href="#addons">Add-ons</a>
                        <ul class="nav">
                            <li><a href="#dropbox"><i class="icon-chevron-right"></i> Dropbox</a></li>
                            <li><a href="#github"><i class="icon-chevron-right"></i> GitHub</a></li>
                            <li><a href="#amazon"><i class="icon-chevron-right"></i> Amazon S3</a></li>
                            <li><a href="#figshare"><i class="icon-chevron-right"></i> FigShare</a></li>
                            <li><a href="#dataverse"><i class="icon-chevron-right"></i> Dataverse</a></li>
                        </ul>
                    </li>
                    <li>
                        <a href="#metrics">Metrics</a>
                        <ul class="nav">
                            <li><a href="#citations"><i class="icon-chevron-right"></i> Citations</a></li>
                            <li><a href="#statistics"><i class="icon-chevron-right"></i> Statistics</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>

        <div class="col-md-9">
            <div class="row text-center" style="margin-bottom: 20px;">
                <div id="start" class="headOne padded anchor">Getting Started</div>
                <div id="start-one"></div>
                <img class="gs-count" src="/static/img/one_big.gif">
                <p class="lead">When developing your idea, you can use the OSF to organize your background research, coordinate with potential collaborators, and pre-register hypotheses.</p>
                <div class="gs-video" style="width: 550px; height: 309px;">
                    <div class="youtube" id="lq4LBjhbB4U" style="width: 550px; height: 309px;"></div>
                </div>
                <br>
                <div id="start-two"></div>
                <img class="gs-count" src="/static/img/two_big.gif">
                <p class="lead">Keep yourself and your collaborators on point while collecting data by using the OSF. Make sure everyone has the resources they need by uploading files, connecting other services like FigShare or GitHub, and adding contributors. </p>
                <div class="gs-video" style="width: 550px; height: 309px;">
                    <div class="youtube" id="VBCaeC7eFI8" style="width: 550px; height: 309px;"></div>
                </div>
                <br>
                <div id="start-three"></div>
                <img class="gs-count" src="/static/img/three_big.gif">
                <p class="lead">Share your research by making your project public and tagging it appropriately. OSF visitors will be able to cite and comment on your work, and you will be able to measure your impact using new altmetrics.</p>
                <div class="gs-video" style="width: 550px; height: 309px;">
                    <div class="youtube" id="lpHswwbX2Ek" style="width: 550px; height: 309px;"></div>
                </div>
            </div>
            <br><br><br><br><br><br>

            <p class="subHeadFour text-center anchor" id="structure">Structuring Your Work:</p>
            <span id="dashboards" class="anchor"></span>
            <div class="row">
                <p class="gs-header">Dashboards</p>
                <p>The Dashboard displays all of your projects and their components in the Project Organizer, and is linked in the black navigation bar at the top of the page. From the Project Organizer, you can open any of your projects or components by clicking on the "open" icon to the right of the project's name.</p>
                <br /><div><img src="/static/img/help/go-to-project.gif" class="img-responsive"></div><br />
                <p>You can shrink or expand each project to display nested components by clicking the + or - to the left of the projects name. A more detailed description of the <a href="#organizer">Project Organizer</a> is below.</p>
                <br /><div><img src="/static/img/help/expand-collapse.gif" class="img-responsive"></div><br />
            </div>
            <span id="projects" class="anchor"></span>
            <div class="row">
                <p class="gs-header">Projects</p>
                <p>Projects are the largest form of categorization that the OSF supports. A project could be an experiment, a lab group, or a paper–anything that has contributing members and files or explanatory texts/images.</p>
                <div class="gs-video">
                    <div class="youtube" id="4GBfBnO_7Ks" style="width: 560px; height: 315px;"></div>
                </div>
                <p>When you click on a project to open it, you are taken to the Project Overview page. This page provides access to the features of the project via a gray navigation bar, as well as an overview of the components, files, tags, history, and wiki associated with the project.</p>
                <div class="gs-video">
                    <div class="youtube" id="FxYFEsMmoEI" style="width: 560px; height: 315px;"></div>
                </div>
            </div>
            <span id="components" class="anchor"></span>
            <div class="row" >
                <p class="gs-header">Components</p>
                <p>Components are like folders in your project. You can assign a component a category upon its creation (data, materials, projects, etc.). A component that is categorized as a project can have more components added within it.</p>
                <div class="gs-video">
                    <div class="youtube" id="d9gxOH15EPk" style="width: 560px; height: 315px;"></div>
                </div>
                <p>Components come with their own privacy settings, contributors, wikis, add-ons, and files.</p>
                <p>To delete a component or project, visit its page and go to "Settings" in the grey navigation bar under the component's title. This will also delete that component's wiki.</p>
                <p>A particular project and component structure that is useful for multiple projects can be used as a template when creating new projects.</p>
            </div>
            <span id="files" class="anchor"></span>
            <div class="row" >
                <p class="gs-header">Files</p>
                <p>Each project and component can have its own set of files. This allows you to organize your files into meaningful groups like datasets or background research.</p>
                <p>To upload a file, click on "Files" in the grey navigation bar under the Project/Component's title. Here you can drag the file from your desktop on to the screen to upload, or click on the upload button in the actions column.</p>
                <div class="gs-video">
                    <div class="youtube" id="Q-fbk_6fG8Y" style="width: 560px; height: 315px;"></div>
                </div>
                <p>Each file is given a unique URL.</p>
                <p>To download a file from a project, click the download button in the actions column.</p>
                <p>You can delete files by clicking  the ‘X’ that appears when you hover over the file.</p>
                <p>Only contributors of that component with writing privileges can add or delete a file. If a component is set to be private, then no one will be able to see the enclosed files, but public components and projects allow anyone to download their materials.</p>
            </div>
            <span id="links" class="anchor"></span>
            <div class="row" >
                <p class="gs-header">Links</p>
                <p>Links are an alternative to building a component within a project. Adding a link to a project means that instead of building a component within the parent project, the component exists separately and is only being pointed to from the present project.</p>
                <p>Any existing public project can be a link.</p>
                <p>Linking is useful if you want to reference another's work or indicate that something is part of a larger project, while still allowing it to exist independently.</p>
                <p>A link can be by visiting the project you want to add the link to. Click "Add Links" in the components section of your project dashboard and search for the project you wish to link to.</p>
                <div class="gs-video">
                    <div class="youtube" id="bdhHoGiwvYg" style="width: 560px; height: 315px;"></div>
                </div>
            </div>
            <span id="forks" class="anchor"></span>
            <div class="row" >
                <p class="gs-header">Forks</p>
                <p>Forking a project means you have created a copy of it into your dashboard, and can change that copy for your own purposes. You will be the only contributor to the forked project until you add others.</p>
                <p>Forks will automatically reference the original project as a functional citation.  Over time, the network of forks trace the evolution of project materials.</p>
                <p>To fork a project, visit the project and click the button at the top right of the page. This will give you several options on how you can duplicate a project. Click "Fork" and a fork will be created.</p>
                <div class="gs-video">
                    <div class="youtube" id="WDSsM3xr4mY" style="width: 560px; height: 315px;"></div>
                </div>
                <p>A <a href="#links">linked</a> project can also easily be turned into a fork. If you were originally linking to a project but would like to make edits to the linked project, from your project dashboard you can find the linked project and hit the small fork button.</p>
                <div class="gs-video">
                    <div class="youtube" id="3F8QC5S_uyU" style="width: 560px; height: 315px;"></div>
                </div>
            </div>
            <span id="registrations" class="anchor"></span>
            <div class="row">
                <p class="gs-header">Registrations</p>
                <p>Registrations are permanent, read only copies of a project. Registration saves the state of a project at a particular point in time - such as right before data collection, or right when a manuscript is submitted.</p>
                <p>To register a project, click on the button in the grey navigation bar. Click on "New Registration", select a meta-data template, fill it out, and then confirm the registration.</p>
                <div class="gs-video">
                    <div class="youtube" id="o9elWNmKRq0" style="width: 560px; height: 315px;"></div>
                </div>
                <p>A registration exists at a separate, permanent URL that is linked to the project.  Then, you can continue editing and revising the project.</p>
            </div>
            <span id="organizer" class="anchor"></span>
            <div class="row">
                <p class="gs-header">Project Organizer</p>
                <p> In addition to displaying your projects, components, and registrations, the Project Organizer makes it easy for you to arrange your projects and components into folders that make sense for your application. Your projects and registrations will be all be shown in Smart Folders called “All My Registrations” and “All My Projects.” Other folders can be created to help you organize projects or components you might like to see grouped in a different way. For example, you may have many projects and find the list overwhelming. It will be helpful for you to have a folder containing only projects or components you work with most often. Alternatively, you might want to be able to easily access all of your analysis scripts from all of your projects. You can create a folder and add to it only analysis scripts components. </p>
                <p>To create a folder, click the “New Folder” button above the Project Organizer and give the folder a name.  </p>
                <br /><div><img src="/static/img/help/new-folder-1.gif" class="img-responsive"></div><br />
                <p>Then simply drag and drop projects or components you’d like associated with this folder, or click on the folder name and choose “Add Existing Project.” </p>
                <br /><div><img src="/static/img/help/drag-project-to-folder.gif " class="img-responsive"></div><br />
                <p> It is important to understand that dropping projects or components into these folders will not change the structure of the original projects themselves, but simply create a new way for you to access your projects and components.</p>
                <p>Folders can be rearranged by dragging and dropping them wherever you like. Folders can be renamed by clicking on the “info” icon adjacent to the folder, and then clicking on the pencil icon next to the folder name. Projects and components can be renamed in this way too. Folders can be deleted by clicking on the “info” icon and choosing “Delete Folder.”</p>
                <br /><div><img src="/static/img/help/rename-folder.gif" class="img-responsive"></div>
            </div>
            <br><br><br><br><br><br>
                
            <p class="subHeadFour text-center anchor" id="sharing">Sharing Your Work:</p>
            <span id="contributors" class="anchor"></span>
            <div class="row">
                <p class="gs-header">Contributors</p>
                <p>Adding contributors to a project allows credit to be given to those who have worked on the project, and allows them to make changes to the project.</p>
                <p>Admins on a project can add contributors by visiting the "Sharing" tab in the grey navigation bar under the project's name. Click on the top link labeled "Click to add a contributor." A pop-up will appear where you can search for a person to add. If they have an OSF account, their name will appear and you can add them and select their privileges. If they do not have an OSF account, you can provide them as an unregistered user and they will be notified by email.  You can select what components you would like to add them to.</p>
                <div class="gs-video">
                    <div class="youtube" id="acJBswJkCGo" style="width: 560px; height: 315px;"></div>
                </div>
                <p><strong>Contributor permissions</strong> are the rules that govern who can see or edit a project. When a project is made, the creator is automatically the administrator, meaning that they can add other people and make changes to the project. The admin can add contributors and make them administrators as well, or they can assign the other contributors to read or read & write priveleges.<p>
                <p>Reading privileges means that the contributor can see any project or component they are listed as a contributor on.</p>
                <p>Reading and writing privileges means that the contributor can see and edit any project or component they are a contributor on, but they cannot add or remove contributors like an administrator.</p>
                <P>Admins can also affect the order in which contributors are listed. To re-order, just click on a contributor and drag and drop them to their new position.</P>
                <div class="gs-video">
                    <div class="youtube" id="iU3ZVF8Lc3M" style="width: 560px; height: 315px;"></div>
                </div>
            </div>
            <span id="privacy" class="anchor"></span>
            <div class="row">
                <p class="gs-header">Privacy</p>
                <p>All projects are private by default. However, you can choose to make your project's contents available for anyone to view. </p>
                <p>Components you have added can have their own privacy settings. Making the project public does not make all of its components public. For example, you can make your methodology component public, but leave the data in a private component.</p>
                <p>Once you make a project public, you can gain more feedback about the impact of your work by tracking how many people that are visiting your projects and downloading or forking your research materials. You can also create a watchlist of other projects that interest you. </p>
                <div class="gs-video">
                    <div class="youtube" id="vs06zE77110" style="width: 560px; height: 315px;"></div>
                </div>
            </div>
            <span id="viewonly" class="anchor"></span>
            <div class="row">
                <p class="gs-header">View-only Links</p>
                <p>View-only links can be created for sharing your projects or components so that people can view - but not edit - them. These links can be anonymized, to remove contributors’ names from the project and associated logs, for use in blinded peer review. </p>
                <p>To create a view-only link, click on the “Sharing” tab, and scroll down to the “View-only links” section. Click “create a link,” give the link a name, and chose the project or component(s) you’d like to link to.</p>
            </div>
            <span id="comments" class="anchor"></span>
            <div class="row">
                <p class="gs-header">Comments</p>
                <p>Commenting can be enabled for any OSF project. To leave a comment on a project, if the administrators have allowed chat, you will see blue speech bubbles in the top right corner of your screen. Click on those speech bubbles and add your comment in the text box.</p>
                <div class="gs-video">
                    <div class="youtube" id="a0ancSamyq4" style="width: 560px; height: 315px;"></div>
                </div>
                <p>You may find that you can view comments but not leave one. That is the administrator's choice, and it reflects their decision to only allow contributors to comment on the project.</p>
                <p>To change your project's comment settings, visit "Settings" in the grey navigation bar below the project title. Select your preference under "Configure Commenting" and submit your changes. </p>
            </div>
            <br><br><br><br><br><br>

            <p class="subHeadFour text-center anchor" id="addons">OSF Add-ons:</p>
            <span id="dropbox" class="anchor"></span>
            <div class="row" >
                <p class="gs-header">Dropbox Add-on</p>
                 <p>To link a Drobpox folder to a project/component, visit the project you want to add a Dropbox folder to. Then go to "Settings" in the grey navigation bar. Check "Dropbox" under "Select Add-ons" to enable the add-on. Read, then click “OK” on the pop-up, then submit.</p>
                <p>Then, authenticate with Dropbox by clicking the "Authorize" button. Once you have said "OK" you can choose the folder you would like to add to your OSF project.</p>
                <div class="gs-video">
                    <div class="youtube" id="0iFtgPfYSg4" style="width: 560px; height: 315px;"></div>
                </div>
            </div>
            <span id="github" class="anchor"></span>
            <div class="row">
                <p class="gs-header">GitHub Add-on</p>
                 <p>To link a GitHub repository to a project/component, visit your profile settings by clicking the gear in the top right of the page. Check "GitHub" under "Select Add-ons" to enable the add-on.</p>
                <p>Then, authenticate with GitHub by clicking the "Create Access Token" button and following the instructions on the GitHub page. Once you have created the access token in your user profile, you will not need to follow those first few steps again. </p>
                <div class="gs-video">
                    <div class="youtube" id="vZAL9BEBcGg" style="width: 560px; height: 315px;"></div>
                </div>
                <p>After creating the access token for your user profile, visit the project you want to add a GitHub repository to. Click on the project name then go to "Settings" in the grey navigation bar. Select the Github add-on by clicking “OK” on the pop-up, then submitting. </p>
                <p>Authorize the Github repository by clicking the blue button. Once you have authorized GitHub then you need to either select a repository or create a new one.</p>
                <div class="gs-video">
                    <div class="youtube" id="u61HCU2TL4M" style="width: 560px; height: 315px;"></div>
                </div>
            </div>
            <span id="amazon" class="anchor"></span>
            <div class="row">
                <p class="gs-header">Amazon Simple Storage Service Add-on</p>
                <p>To link Amazon Simple Storage Service bucket to a project/component, visit your profile settings by clicking the gear in the top right of the page. Check "Amazon Simple Storage Service" under "Select Add-on.”</p>
                <p>Next, authenticate Amazon Simple Storage Service by entering the access key and secret key. Then, click “Submit.”</p>
                <div class="gs-video">
                    <div class="youtube" id="q_Sc_1XNQdI" style="width: 560px; height: 315px;"></div>
                </div>
                <p>Once you have enabled Amazon Simple Storage Service in your user settings, you won’t need to do those previous steps again. To associate a bucket with a project, visit the project you want to add a Amazon Simple Storage Service bucket to. Go to "Settings" in the grey navigation bar. Select the Amazon Simple Storage Service add-on under “Select Add-ons” and click“OK” on the pop-up. Then, submit your new settings.</p>
                <p>Once you have authorized Amazon Simple Storage then you need to either select a buckets from the dropdown or create one.</p>
                <div class="gs-video">
                    <div class="youtube" id="kFbNYVLY52A" style="width: 560px; height: 315px;"></div>
                </div>
            </div>
            <span id="figshare" class="anchor"></span>
            <div class="row">
                <p class="gs-header">FigShare</p>
                <p>Currently, the OSF only supports linking FigShare projects to an OSF project–not individual files or articles.</p>
                <p>To link a FigShare project to an OSF project, first visit your profile settings by clicking the gear in the top right of the page. Check "FigShare" under "Select Add-on.”</p>
                <p>Next, authenticate FigShare by clicking "Create Access Token" and following the instructions on the FigShare website. Once you have enabled FigShare in your user settings, you won’t need to do those previous steps again. </p>
                <div class="gs-video">
                    <div class="youtube" id="jTHaoUDn3G0" style="width: 560px; height: 315px;"></div>
                </div>
                <p>To associate a FigShare project with an OSF project, visit the project you want to add the FigShare project to. Go to "Settings" in the grey navigation bar. Select the FigShare add-on under “Select Add-ons” and click “OK” on the pop-up. Then, submit your new settings.</p>
                <p>Still in your project settings, now click the authorize button for FigShare under "Configure Add-ons" and then select the project you want to add.</p>
                <div class="gs-video">
                    <div class="youtube" id="PYbDtghU1VI" style="width: 560px; height: 315px;"></div>
                </div>
                <p>Commenting can be enabled for any OSF project. To leave a comment on a project, if the administrators have allowed chat, you will see blue speech bubbles in the top right corner of your screen. Click on those speech bubbles and add your comment in the text box.</p>
                <div class="gs-video">
                    <div class="youtube" id="a0ancSamyq4" style="width: 560px; height: 315px;"></div>
                </div>
                <p>You may find that you can view comments but not leave one. That is the administrator's choice, and it reflects their decision to only allow contributors to comment on the project.</p>
                <p>To change your project's comment settings, visit "Settings" in the grey navigation bar below the project title. Select your preference under "Configure Commenting" and submit your changes. </p>
            </div>
            <span id="dataverse" class="anchor"></span>
            <div class="row">
                <p class="gs-header">Dataverse</p>
                 <p>Currently, the OSF only supports linking Dataverses that you have already released on the <a href="http://thedata.harvard.edu/dvn/">Harvard Dataverse Network</a>.</p>
                <p>To link a Dataverse study to a project/component, visit the project you want to add a Dataverse study to. Then go to "Settings" in the grey navigation bar. Check "Dataverse" under "Select Add-ons" to enable the add-on. Read, then click "OK" on the pop-up, then submit.</p>
                <p>Next, authenticate with Dataverse by entering your Dataverse username and password and clicking "Submit". You can then choose the Dataverse study you would like to add to your OSF project. Click "Submit" to save your settings.</p>
                <div class="gs-video">
                    <div class="youtube" id="QzGJGWgy8Qo" style="width: 560px; height: 315px;"></div>
                </div>
                <p>Contributors to your project will have access to both released and draft versions of your study, but only the most recent release will be made public alongside your OSF project.</p>
            </div>
            <br><br><br><br><br><br>
            <p class="subHeadFour text-center anchor" id="metrics">Metrics:</p>
            <span id="citations" class="anchor"></span>
            <div class="row">
            <p class="gs-header">Citations</p>
             <p>Every project, component, file, and user has a unique URL on the OSF. This means that anything you upload and make public on the OSF can be cited, giving you credit for your work.</p>
                <p>To find a pre-formatted citation for a project, look directly below the grey navigation bar on the project's page and you will see the URL to be cited. If you click "more" then you ill see the APA, MLA, and Chicago citations.</p>
                <div class="gs-video">
                    <div class="youtube" id="BeJhLJEzrNw" style="width: 560px; height: 315px;"></div>
                </div>
            </div>
            <span id="statistics" class="anchor"></span>
            <div class="row">
                <p class="gs-header">Statistics</p>
                <p>Every project comes with a statistics page where you can view information on how often people are visiting your project and where they are being referred from.</p>
                <P>The information displayed on the statistics page can be changed. From the statistics page of your project (found by clicking "Statistics" in the grey navigation bar), click on "Widgets & Dashboard." Select the widget you wish to add by clicking on the orange arrow to the right of the widget's name.</P>
                <div class="gs-video">
                    <div class="youtube" id="WKjyILQzZv0" style="width: 560px; height: 315px;"></div>
                </div>
            </div>
        </div>
    </div>
    <script type="text/javascript" src="/static/vendor/youtube/youtube-loader.js"></script>
</%def>
