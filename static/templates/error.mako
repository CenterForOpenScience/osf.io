<%inherit file="base.mako"/>
<%def name="title()">Error</%def>
<%def name="content()">
<div class="container" style="margin-top: 30px;">
    <div class='row'>
        <div class='span12'>
            <h2 id='error' data-http-status-code="${code}">${message_short}</h2>
            <p>${message_long}</p>
            % if referrer:
                <p><a href="${referrer}">Back</a></p>
            % endif
        </div>
    </div>
</div>
</%def>
