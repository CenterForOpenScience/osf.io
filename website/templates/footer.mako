
<% from datetime import datetime %>
<div class="footer-wrapper">
    <div class="footer-row">
        <span>
            <a href="${footer_links['cos']}">
                Center for Open Science
            </a>
        </span>
        <div class="footer-social-links-list">
            <a class="footer-logo" href="${footer_links['github']}" aria-label="Twitter">
                <span class="fa-stack">
                    <i class="fa-brands fa-github-square fa-2x"></i>
                </span>
            </a>
            <a class="footer-logo" href="${footer_links['github']}" aria-label="LinkedIn">
                <span class="fa-stack">
                    <i class="fa-brands fa-linkedin fa-2x"></i>
                </span>
            </a>
            <a class="footer-logo" href="${footer_links['github']}" aria-label="Bluesky">
                <span class="fa-stack">
                    <i class="fa-solid fa-square fa-stack-2x"></i>
                    <i class="fa-brands fa-bluesky fa-stack-1x fa-inverse"></i>
                </span>
            </a>
            <a class="footer-logo" href="${footer_links['github']}" aria-label="Mastodon">
                <span class="fa-stack">
                    <i class="fa-solid fa-square fa-stack-2x"></i>
                    <i class="fa-brands fa-mastodon fa-stack-1x fa-inverse"></i>
                </span>
            </a>
        </span>
    </div>
</div>
<div class="footer-row">
    <div class="footer-links-list">
        <a href="${footer_links['terms']}">
            Terms&nbsp;of&nbsp;Use
        </a>
        |
        <a href="${footer_links['privacyPolicy']}">
            Privacy&nbsp;Policy
        </a>
        |
        <a href="${footer_links['statusPage']}">
            Status
        </a>
        |
        <a href="${footer_links['apiDocs']}">
            API
        </a>
        |
        <a href="${footer_links['topGuidelines']}">
            TOP Guidelines
        </a>
    </div>
    <span>
        Copyright &copy; 2011-${datetime.utcnow().year}
    </span>
</footer>
