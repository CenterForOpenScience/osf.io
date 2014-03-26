<div class="addon-widget" name="${short_name}">
<script src="/addons/static/badges/awardBadge.js"></script>

%if complete:

    <h3 class="addon-widget-header">
          <a href="badges/"><span>${full_name}</span></a>
    </h3>

%if len(assertions) > 0:
  <div class="badge-list">
          %for assertion in reversed(assertions[-6:]):
            <img src="${assertion['image']}" width="64px" height="64px" class="open-badge badge-popover" badge-url="/${assertion['uid']}/json/" data-content="${assertion['description']}" data-toggle="popover" data-title="${assertion['name']}">
          %endfor
          <!-- TODO add ...-->
  </div>
%endif
<script>

$(document).ready(function(){
  $('.badge-popover').popover({
    container: 'body',
    trigger: 'hover'
  });
});

</script>

%else:
        <div mod-meta='{
                "tpl": "project/addon/config_error.mako",
                "kwargs": {
                    "short_name": "${short_name}",
                    "full_name": "${full_name}"
                }
            }'></div>
%endif
</div>
