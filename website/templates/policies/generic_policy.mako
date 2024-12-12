<%inherit file="base.mako"/>

<%def name="content()">
<div id="policy" class="container">
    <div class="row">
        <div class="col-md-12">
            <br>
            ${policy_content}
        </div>
        <div class="col-md-12">
            <br>
            Version history for this policy is available <a href='${POLICY_GITHUB_LINK}'>here</a>
        </div>
    </div>
</div><!-- end container policy -->
</%def>
