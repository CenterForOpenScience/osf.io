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
            <a href='${POLICY_GITHUB_LINK}'>Version history for this policy</a> is available.
        </div>
    </div>
</div><!-- end container policy -->
</%def>
