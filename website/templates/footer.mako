 <% import website.settings %>
        </div>
    </div>
        <div class="footer">
            <div class="container">
                <div class="row">
                    <div class="span1">
                        &nbsp;
                    </div>
                     <div class="span2">
                        <h4>OSF</h4>
                        <ul>
                            <li><a href="/project/4znZP/wiki/home">About</a></li>
                            <li><a href="/faq">FAQ</a></li>
                            <li><a href="/explore">Explore</a></li>
                        </ul>
                    </div>
                    <div class="span3">
                        <h4>Center for Open Science</h4>
                        <ul>
                            <li><a href="https://centerforopenscience.org">Home</a></li>
                            <li><a href="http://centerforopenscience.org/#contact">Contact</a></li>
                            <li><a href="/project/EZcUj/wiki/home" </li>
                        </ul>
                    </div>
                    <div class="span2">
                        <h4>Documentation</h4>
                        <ul>
                            <li><a href="/getting-started">Getting Started</a></li>
                            <li>Developer API</li>
                        </ul>
                    </div>
                    <div class="span2">
                        <h4>Socialize</h4>
                        <ul>
                            <li><a href="https://groups.google.com/forum/#!forum/openscienceframework">Google Group</a></li>
                            <li><a href="http://facebook.com/openscienceframework">Facebook</a></li>
                            <li><a href="http://twitter.com/osframework">Twitter</a></li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        <div class="container copyright">
            <div class="row">
                <div class="span12">
                <p>Copyright &copy; 2011-2013 <a href="http://centerforopenscience.org">CenterforOpenScience.org</a> - Terms of Service | Privacy | Security</p>
                </div>
            </div>
        </div>

        %if website.settings.use_cdn_for_client_libs:
            <div id="fb-root"></div>
            <script>(function(d, s, id) {
              var js, fjs = d.getElementsByTagName(s)[0];
              if (d.getElementById(id)) {return;}
              js = d.createElement(s); js.id = id;
              js.src = "//connect.facebook.net/en_US/all.js#xfbml=1";
              fjs.parentNode.insertBefore(js, fjs);
            }(document, 'script', 'facebook-jssdk'));</script>

            <script type="text/javascript">

              var _gaq = _gaq || [];
              _gaq.push(['_setAccount', 'UA-26813616-1']);
              _gaq.push(['_trackPageview']);

              (function() {
                var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
                ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
                var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
              })();
            </script>
        %endif
    </body>
</html>