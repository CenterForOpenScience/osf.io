<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
    <link href='http://fonts.googleapis.com/css?family=Carrois+Gothic|Inika|Patua+One' rel='stylesheet' type='text/css'>
    <script>
        $(function() {
            $('.subHeadTwo')
                    .on('click', function(e)
                    {
                        $(e.target)
                                .parents('.col-md-4')
                                .children('.featureInfo')[0].style.display="block";
                    }

            );
        });
    </script>

    <div class="hp-banner"></div>
    <div id="hpContainerOne">
        <div id="containerOneHeader">
            <p class ="headOne">Project management with collaborators,<br> project sharing with the public</p>
            <br>
            <p class ="subHeadOne">The OSF organizes materials and data across the research lifecycle and between researchers. </p>
        </div>
        <div class="sign-up img-rounded">
            <div>
                <input type="text" class="form-control" placeholder="Full Name">
                <input type="text" class="form-control" placeholder="Contact Email">
                <input type="text" class="form-control" placeholder="Password">
                <button type="button" class="btn btn-danger">Sign up for the OSF</button>
            </div>
        </div>
    </div>
    <div id="hpContainerTwo">
        <div class="header">
            <p class="headOne">What can the OSF do for you?</p>
            <p class="subHeadOne">Provide features to increase the efficiency and effectiveness of your research</p>
        </div>
        <div class="col-md-12 featureDescriptions">
            <div class="col-md-4 connect">
                <img id="connect" src="/static/img/apart_connect.gif">
                <p><a class="subHeadTwo hpLink">CONNECTIONS</a> with the services you already use</p>
                <div class="featureInfo">The OSF links services together to simplify transitions and facilitate interactions.  For example, connect GitHub and Amazon Simple Storage Service repositories to an OSF project and get the benefits of both in one place.</div>

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
                            $("#connect").attr("src", "/static/img/apart_connect.gif");
                        }
                    );
                });
            </script>

            <div class="col-md-4 archive">
                <img id="archive" src="/static/img/archive.gif">
                <p><a class="subHeadTwo hpLink">ARCHIVING</a> and management of research and collaborations</p>
                <div class="featureInfo">The OSF helps you spend more time doing your research and less time keeping track of it. Our file saving system means no more lost data from crashed drives, disappearing collaborators, or failing memories.</div>
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

            <div class="col-md-4">
                <p><a class="subHeadTwo hpLink">INTEGRATION</a> of private and public workflows</p>
                <div class="featureInfo">Work privately among collaborators and, when you wish, make some or all of your research materials public so that others can download or cite it. As of February 2014, there have been 30,000 downloads from the OSF!</div>
            </div>
        </div>
    </div>
    <div id="hpContainerThree">
        <div class="header">
            <p class="headOne">Free and easy to use</p>
            <p class="subHeadOne">Follow these simple steps to get started. We'll be <a class="hpLink" href="mailto:contact@osf.io">here to help</a> the whole way.</p>
            <div class="col-md-12 padded">
                <p class="subHeadTwo steps"><a class="hpLink" href="https://osf.io/account/">Sign up.</a></p>
                <p class="subHeadTwo steps"><a class="hpLink" href="https://osf.io/getting-started/">Learn how to build a project.</a></p>
                <p class="subHeadTwo steps"><a class="hpLink" href="https://osf.io/explore/activity/">Get inspired.</a></p>
            </div>
            <p class="stepsText">Want more than an answer to a quick question? Feel free to <a class="hpLink" href="mailto:contact@osf.io">email us</a> to schedule a help session or tutorial for you and your collaborators.<br>OSF is backed by the non-profit <a class="hpLink" href="http://centerforopenscience.org/">Center for Open Science</a>.</p>
        </div>

    </div>

</%def>
