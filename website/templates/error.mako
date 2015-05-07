<%inherit file="base.mako"/>
<%def name="title()">${message_short}</%def>
<%def name="content()">
<div class="container">
    <div class='row'>
        <div class='col-md-12'>
            <h2 id='error' data-http-status-code="${code}">${message_short}</h2>
            <p>${message_long}</p>
            % if referrer:
                <p><a href="${referrer}">Back</a></p>
            % endif
        </div>
    </div>
</div>
</%def>
