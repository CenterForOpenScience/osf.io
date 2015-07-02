<%inherit file="base.mako"/>
<%def name="title()">Pre-reg Admin</%def>



<%def name="javascript_bottom()">

<script>
    window.contextVars = $.extend(true, {}, window.contextVars, {
        currentUser: {
            'id': '${user_id}'
        }
    });
</script>

</%def>
