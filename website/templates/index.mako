<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
    <link href='http://fonts.googleapis.com/css?family=Inika:400,700|Patua+One' rel='stylesheet' type='text/css'>
    <link href='http://fonts.googleapis.com/css?family=Carrois+Gothic' rel='stylesheet' type='text/css'>

    <div class="hp-banner"></div>

    <div id="hpContainerOne">
        <div id="containerOneHeader">
            <p class ="headOne">Project management with collaborators,<br> project sharing with the public</p>
            <br>
            <p class ="subHeadOne">The OSF organizes materials and data across the research lifecycle and between researchers. </p>
        </div>
        <div class="sign-up"></div>
    ##            <img src="/Users/johannacohoon/Desktop/untitled1/img/discussions.png">
            </div>
    <div id="hpContainerTwo">
        <div class="header">
            <p class="headOne">What makes the OSF unique?</p>
            <p class="subHeadOne">Features to increase the efficiency and effectiveness of your research</p>
        </div>
        <div class="col-md-12 featureDescriptions">
            <div class="col-md-4">
                <p>Connections with the services you already use</p>
                <div class="featureInfo">OSF supports many workstyles to help you spend more time doing your research and less time keeping track of it.  With our built in file saving system there is no more lost data from crashed drives, disappearing collaborators, or failing memories.</div>
            </div>

            <div class="col-md-4">
                <p>Easy archival and management of your research and collaborations</p>
                <div class="featureInfo">OSF links services together to simplify transitions and facilitate interactions.  For example, connect GitHub and Amazon S3 repositories to an OSF project and get the benefits of both in one place.</div>
            </div>


            <div class="col-md-4">
                <p>Integration of private and public workflows</p>
                <div class="featureInfo">OSF supports many workstyles to help you spend more time doing your research and less time keeping track of it.  With our built in file saving system there is no more lost data from crashed drives, disappearing collaborators, or failing memories.</div>
            </div>

        </div>
    </div>


</%def>
