<% from datetime import datetime %>
<footer class="footer">
    <div class="container-fluid">
        <div class="row">
            <div class="col-sm-12 col-md-8 col-md-offset-2">
                <p>
                    <span>
                        Copyright &copy; 2016-${datetime.utcnow().year}
                    </span>
                    <a href="${footer_links['cos']}">
                        ${_("National Institute of Informatics")}
                    </a>
                    <span>
                        |
                    </span>
                    <a href="${footer_links['terms']}">
                        ${_("Terms&nbsp;of&nbsp;Use") | n}
                    </a>
                    <span>
                        |
                    </span>
                    <a href="${footer_links['privacyPolicy']}">
                        ${_("Privacy&nbsp;Policy") | n}
                    </a>
                    <!--
                    <span>
                        |
                    </span>
                    <a href="${footer_links['statusPage']}">
                        ${_("Status")}
                    </a>
                    -->
                    <!--
                    <span>
                        |
                    </span>
                    <a href="${footer_links['apiDocs']}">
                        API
                    </a>
                    -->
                    <br>
                    <!--
                    <a href="${footer_links['topGuidelines']}">
                        ${_("TOP Guidelines")}
                    </a>
                    -->
                    <!--
                    <span>
                        |
                    </span>
                    <a href="${footer_links['rpp']}">
                        ${_("Reproducibility&nbsp;Project: Psychology") | n}
                    </a>
                    -->
                    <!--
                    <span>
                        |
                    </span>
                    <a href="${footer_links['rpcb']}">
                        ${_("Reproducibility&nbsp;Project: Cancer Biology") | n}
                    </a>
                    -->
                </p>
                <p>
                    <!--
                    <a href="${footer_links['twitter']}" aria-label="Twitter"><i class="fa fa-twitter fa-2x"></i></a>
                    -->
                    <!--
                    <a href="${footer_links['facebook']}" aria-label="Facebook"><i class="fa fa-facebook fa-2x"></i></a>
                    -->
                    <!--
                    <a href="${footer_links['googleGroup']}" aria-label="Google Group"><i class="fa fa-group fa-2x"></i></a>
                    -->
                    <a href="${footer_links['github']}" aria-label="GitHub"><i class="fa fa-github fa-2x"></i></a>
                    <a href="${footer_links['cos']}"><img src=${_("/static/img/footer_logo_EN.png")}></a>
                </p>
            </div>
        </div>
    </div>
</footer>
