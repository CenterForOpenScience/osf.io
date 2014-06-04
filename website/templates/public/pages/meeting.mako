<%inherit file="base.mako"/>
<%def name="title()">${ meeting['name'] } Presentations</%def>

<%def name="content()">

    <h2 style="padding-bottom: 30px;">${ meeting['name'] } Posters & Talks</h2>

    % if meeting['logo_url']:
        <img src="${ meeting['logo_url'] }" class="image-responsive" />
        <br /><br />
    % endif

    % if meeting['info_url']:
        <div><a href="${ meeting['info_url'] }" target="_blank">Add your poster or talk</a></div>
    % endif

    <div style="padding-bottom: 30px;">
        Search results by title or author:
        <input id="gridSearch" />
    </div>
    <div id="grid" style="width: 100%;"></div>

</%def>

<%def name="javascript_bottom()">
    <script type="text/javascript">
        var data = ${data};
        $script('/static/js/conference.js');
        $script.ready('conference', function() {
            new Meeting(data);
        })
    </script>
</%def>
