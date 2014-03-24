<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
    <link href='http://fonts.googleapis.com/css?family=Carrois+Gothic|Inika|Patua+One' rel='stylesheet' type='text/css'>

    <div class="hp-banner"></div>
    <div id="hpContainerOne">
        <div id="containerOneHeader">
            <p class ="headOne"><a href="/news">Project</a> management with collaborators,<br> project sharing with the public</p>
            <br>
            <p class ="subHeadOne">The Open Science Framework (OSF) supports the entire research lifecycle: planning, execution, reporting, archiving, and discovery. </p>
        </div>
        <div class="sign-up img-rounded">
            <div>
                <input type="text" class="form-control" placeholder="Full Name">
                <input type="text" class="form-control" placeholder="Contact Email">
                <input type="text" class="form-control" placeholder="Password">
                <button type="button" class="btn btn-danger">Sign up</button>
            </div>
        </div>
    </div>
    <div id="hpContainerTwo">
        <div class="header center">
            <p class="headOne">What can the OSF do for you?</p>
            <p class="subHeadOne">Provide features to increase the efficiency and effectiveness of your research</p>
        </div>
        <div class="col-md-12 featureDescriptions">
            <div class="col-md-4 center connect">
                <img id="connect" src="/static/img/connect.gif">
                <div class="subHeadTwo center">CONNECTIONS</div>
                <p>with the services you already use</p><br>
                <div class="featureInfo">Link services to simplify transitions and facilitate interactions; e.g., connect OSF to your GitHub and Amazon S3 repositories and all three work together!</div>

            </div>

            <script>
                $(document).ready(function()
                {
                    $('.connect').hover(
                            function()
                            {
                                $("#connect").attr("src", "/static/img/connect-motion.gif");
                            },
                            function()
                            {
                                $("#connect").attr("src", "/static/img/connect.gif");
                            }
                    );
                });
            </script>

            <div class="col-md-4 center archive">
                <img id="archive" src="/static/img/archive.gif"><br>
                <div class="subHeadTwo center">ARCHIVING</div>
                <p>and management of research and collaborations</p>
                <div class="featureInfo">Spend more time doing your research and less time keeping track of it. No more lost data from crashed drives, disappearing collaborators, or failing memories.</div>
            </div>
            <script>
                $(document).ready(function()
                {
                    $('.archive').hover(
                            function()
                            {
                                $("#archive").attr("src", "/static/img/archive-motion.gif");
                            },
                            function()
                            {
                                $("#archive").attr("src", "/static/img/archive.gif");
                            }
                    );
                });
            </script>

            <div class="col-md-4 center integrate">
                <img id="integrate" src="/static/img/open.gif">
                <div class="subHeadTwo">INTEGRATION</div>
                <p>of private and public workflows</p><br>
                <div class="featureInfo">Work privately among collaborators and, when you wish, make some or all of your research materials public for others to use and cite.</div>
            </div>
            <script>
                $(document).ready(function()
                {
                    $('.integrate').hover(
                            function()
                            {
                                $("#integrate").attr("src", "/static/img/sign-motion.gif");
                            },
                            function()
                            {
                                $("#integrate").attr("src", "/static/img/open.gif");
                            }
                    );
                });
            </script>
        </div>
    </div>
    <div class="spacer dashes">

    </div>
    <div id="hpContainerThree">
        <div class="header center">
            <p class="headOne">Free and easy to use</p>
            <p class="subHeadOne">Follow these simple steps to get started. We'll be <a class="hpLink" href="mailto:contact@osf.io">here to help</a> the whole way.</p>
            <div class="col-md-12 padded">
                <p class="subHeadThree  steps"><a class="hpLink" href="https://osf.io/account/">Sign up.</a></p>
                <p class="subHeadThree  steps"><a class="hpLink" href="https://osf.io/getting-started/">Learn how to build a project.</a></p>
                <p class="subHeadThree  steps"><a class="hpLink" href="https://osf.io/explore/activity/">Get inspired.</a></p>
            </div>
            <p class="stepsText">Want more than an answer to a quick question? Feel free to <a class="hpLink" href="mailto:contact@osf.io">email us</a> to schedule a help session or tutorial for you and your collaborators.<br>OSF is backed by the non-profit <a class="hpLink" href="http://centerforopenscience.org/">Center for Open Science</a>.</p>
        </div>

    </div>

</%def>
