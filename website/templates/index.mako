<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
<div class="container" >

    <div style="padding-top: 50px">
        <div id="welcomeCarousel" class="carousel slide" data-ride="carousel">

          <!-- Wrapper for slides -->
          <div class="carousel-inner" style="height: 430px"  >

            <div class="item active row"  data-pause="hover" style="padding: 60px 40px 60px 40px;">
                <div class="col-md-12 col-sm-offset-2" style = "font-size: 50px" class = "lead">
                    <p><strong>OSF now supports Dropbox</strong></p>
                    <div class="row" style="padding-top: 20px">
                        <div class="col-md-2" style="padding-top: 10px; height: 300px"> <img src="/static/img/dropbox-notext.png" class="img-responsive"> </div>
                        <div class="col-md-6" >
                            <p style="font-size: 30px"  class="lead">Connect a Dropbox folder with your OSF projects.</p>
                            <p style="font-size: 30px"  class="lead"><a href="https://osf.io/getting-started#dropbox" style="text-decoration: none">Learn how!</a></p>
                            </div>
                    </div>
                </div>
            </div>
            <div class="item row"  data-pause="hover" style="padding: 60px 40px 60px 40px;">
                <div class="col-md-12 col-sm-offset-2" style = "font-size: 40px" class = "lead">
                    <p><strong>Have code you want to attach<br> to your research?</strong></p>
                    <div class="row" style="padding-top: 20px">
                        <div class="col-md-2" style="padding-top: 10px; padding-left: 35px"><img src="/static/img/Octocat.png" style="width: 200px"></div>
                        <div class="col-md-6 col-md-offset-1" ><p style="font-size: 30px"  class="lead">
                            <a href="/getting-started#github" style="text-decoration: none">Add a GitHub repo</a>
                                to your project<br> by visiting project settings.</p></div>
                    </div>
                </div>
            </div>
            <div class="item row" data-pause="hover" style="padding: 60px 40px 60px 30px" >
                <div class="col-md-9 col-md-offset-3">
                    <p style = "font-size: 50px" class = "lead">Not sure where to begin?</p>
                </div>
                <div class="col-md-6 col-md-offset-3">
                    <p style = "font-size: 20px" class = "lead FP_Center">We're here to help. Visit the pages below or <a href="mailto:contact@cos.io"  style="text-decoration: none">contact us</a> with questions.</p>
                </div>
                <div class="col-md-6 col-md-offset-4">
                <a class="btn btn-primary span3 text-center" href="/getting-started" style="font-size: 20px; text-decoration: none">Getting Started</a>
                <a class="btn btn-primary span3 text-center" href="/explore/activity/" style="font-size: 20px; text-decoration: none">Browse Projects</a>
                </div>
            </div>

          </div>

          <!-- Controls -->
          <a id="carousel-control-left-blue" class="left carousel-control" href="#welcomeCarousel" data-slide="prev" >
              <span class="glyphicon glyphicon-chevron-left"></span>
          </a>
          <a id="carousel-control-right-blue" class="right carousel-control" href="#welcomeCarousel" data-slide="next">
              <span class="glyphicon glyphicon-chevron-right"></span>
          </a>
        </div>
    </div>

    <div class="row">

        <div style="padding-top: 30px">
        <hr class="hrBlue">
            <div class="col-md-8" style="margin-right: 50px">
                <div class="tab-content ">
                    <div class="tab-pane active fade in">
                        <h1 class="FP_Question">Who are you?</h1>
                        <p class="lead">The OSF is designed to build collaborative scientific culture. Click to the right and tell us who you are
                         to find out where to start.</p>
                    </div>
                    <div class="tab-pane fade in" id="scientist">
                        <H1 class="FP_Header ">I am a scientist.</h1>
                        <p class="lead" >The OSF is a place for scientists to organize, archive, network, and collaborate. An account on the OSF
                        will facilitate your workflow, help you measure your impact, and is available <em><a href="/faq">
                        for free</a></em>.</p>
                        <p class="lead">Visit our <a href="/getting-started">Getting Started page</a> to learn about
                        the features the OSF offers. Stay tuned to keep up with additional features as they roll out. </p>
                    </div>
                    <div class="tab-pane fade in" id="journal">
                        <h1 class="FP_Header">I represent a journal, funder, or society.</h1>
                        <p class="lead">Journals, funders and scientific societies can use the OSF as back-end infrastructure for preregistration,
                        data and materials archiving, and other administrative functions.</p>
                        <p class="lead">We are working to connect services and APIs so that you don't have to.</p>
                        <p class="lead">Email contact@centerforopenscience.org for more information.</p>
                    </div>
                    <div class="tab-pane fade in" id="developer">
                        <h1 class="FP_Header">I am a developer.</h1>
                        <p class="lead">Developers can contribute to the OSF and other open-source projects, or connect their projects to OSF via API.</p>
                        <p class="lead">To learn more you can watch the video below from SciPy, find us on <a href="https://github.com/centerforopenscience"
                        target="_blank">GitHub</a>, or contact developer@centerforopenscience.org.</p>
                        <p class="lead">We are also currently looking for developers to join our team. To see our openings, visit
                         <a href="http://centerforopenscience.org/jobs/" target="_blank">cos.io/jobs</a>.
                    </div>
                </div>
            </div>



            <div class="col-md-3 verticalline" style="padding: 35px 0px 25px 20px">
                <ul class="nav nav-pills nav-stacked">
                    <li class="lead" style="font-color:purple; padding-left: 15px" id="FP_great"><strong>I am a...</strong></li>
                    <li class="lead"><a href="#scientist" data-toggle="pill" >Scientist</a></li>
                    <li class="lead"><a href="#journal" data-toggle="pill">Journal, Funder, or Society</a></li>
                    <li class="lead"><a href="#developer" data-toggle="pill">Developer</a></li>
                </ul>
            </div>

        </div>

    </div>
    <hr class="hrBlue">
    <div style="padding: 25px 10px 150px 10px;">
            <div class="col-md-6">
                <h3 class="lead">Open Science Framework Demonstration</h3>
                <object><param name="movie" value="//www.youtube.com/v/c6lCJFSnMcg?hl=en_US&amp;version=3&amp;rel=0"></param><param name="allowFullScreen" value="true"></param><param name="allowscriptaccess" value="always"></param><embed src="//www.youtube.com/v/c6lCJFSnMcg?hl=en_US&amp;version=3&amp;rel=0" type="application/x-shockwave-flash" width="450" height="315" allowscriptaccess="always" allowfullscreen="true"></embed></object>
            </div>
            <div class="col-md-6" style="padding-bottom: 100px">
                <h3  class="lead">Open Science Framework at SciPy</h3>
                <object><param name="movie" value="//www.youtube.com/v/WRadGRdkAIQ?hl=en_US&amp;version=3&amp;rel=0"></param><param name="allowFullScreen" value="true"></param><param name="allowscriptaccess" value="always"></param><embed src="//www.youtube.com/v/WRadGRdkAIQ?hl=en_US&amp;version=3&amp;rel=0" type="application/x-shockwave-flash" width="450" height="315" allowscriptaccess="always" allowfullscreen="true"></embed></object>
            </div>
    </div>

</div>
</%def>
