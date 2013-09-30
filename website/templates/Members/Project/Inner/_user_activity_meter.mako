<%def name="print_ua_meter(logs, profileId, rescale_ratio, profileFullname)">
    <%
        from framework import get_user
        from website.project import get_node

        # Counters
        ua_count    = 0 # user activity in project, base length of green bar
        total_count = len(logs)
        if logs is not None:
            for i, log in enumerate(logs):
                if log is not None:
                    tuser = log.user
                    if tuser is not None and tuser._primary_key==profileId:
                       # increment counter if log author is current user
                       ua_count += 1
        non_ua_count = total_count - ua_count # base length of blue bar

        # Normalize over all nodes
        max_width = 335 # max width in px for the stacked bar
        # get css widths for bars
        ua = ua_count / rescale_ratio * max_width
        non_ua = non_ua_count / rescale_ratio * max_width
    %>


    <!--Stacked bar to visualize user activity level against total activity level of a project -->
    <!--Length of the stacked bar is normalized over all projects -->
    <ul class="meter-wrapper">
        <li class="ua-meter" data-toggle="tooltip" title="${profileFullname} made ${ua_count} contributions" style="width:${ua}px;"></li>
        <li class="pa-meter" style="width:${non_ua}px;"></li>
        <li class="pa-meter-label">${total_count} contributions</li>
    </ul>
    <script>
        $('.ua-meter').tooltip();
    </script>

</%def>