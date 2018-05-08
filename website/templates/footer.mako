<% from datetime import datetime %>
<footer class="footer">
    <div class="container-fluid">
        <div class="row">
            <div class="col-sm-12 col-md-8 col-md-offset-2">
                <p>
                    <span>
                        Copyright &copy; 2011-${datetime.utcnow().year}
                    </span>
                    <a href="${footer_links['cos']}">
                        Center for Open Science
                    </a>
                    <span>
                        |
                    </span>
                    <a href="${footer_links['terms']}">
                        Terms&nbsp;of&nbsp;Use
                    </a>
                    <span>
                        |
                    </span>
                    <a href="${footer_links['privacyPolicy']}">
                        Privacy&nbsp;Policy
                    </a>
                    <span>
                        |
                    </span>
                    <a href="${footer_links['statusPage']}">
                        Status
                    </a>
                    <span>
                        |
                    </span>
                    <a href="${footer_links['apiDocs']}">
                        API
                    </a>
                    <br>
                    <a href="${footer_links['topGuidelines']}">
                        TOP Guidelines
                    </a>
                    <span>
                        |
                    </span>
                    <a href="${footer_links['rpp']}">
                        Reproducibility&nbsp;Project: Psychology
                    </a>
                    <span>
                        |
                    </span>
                    <a href="${footer_links['rpcb']}">
                        Reproducibility&nbsp;Project: Cancer Biology
                    </a>
                </p>
                <p>
                    <a href="${footer_links['twitter']}" aria-label="Twitter"><i class="fa fa-twitter fa-2x"></i></a>
                    <a href="${footer_links['facebook']}" aria-label="Facebook"><i class="fa fa-facebook fa-2x"></i></a>
                    <a href="${footer_links['googleGroup']}" aria-label="Google Group"><i class="fa fa-group fa-2x"></i></a>
                    <a href="${footer_links['github']}" aria-label="GitHub"><i class="fa fa-github fa-2x"></i></a>
                    <a href="${footer_links['googlePlus']}" aria-label="Google Plus" rel="publisher"><i class="fa fa-google-plus fa-2x"></i></a>
                </p>
            </div>
        </div>
    </div>
</footer>
