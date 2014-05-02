<div class="addon-widget" name="${short_name}">

%if complete:

    <h3 class="addon-widget-header">
          <a href="badges/"><span>Latest Badges</span></a>
    </h3>

%if len(assertions) > 0:
  <div class="badge-list">
          %for assertion in reversed(assertions[-6:]):
            <img src="${assertion.badge.image}" width="64px" height="64px" class="open-badge badge-popover" badge-url="/badge/assertion/json/${assertion._id}/" data-content="${assertion.badge.description_short}" data-toggle="popover" data-title="<a href=&quot;/${assertion.badge._id}/&quot;>${assertion.badge.name}</a>- <a href=&quot;${assertion.awarder.owner.profile_url}&quot;>${assertion.awarder.owner.fullname}</a>">
          %endfor
          %if len(assertions) > 6:
            <a href="badges/" class="ellipse">...</a>
          %endif
  </div>

  <style type="text/css">
    .badge-list img {
      cursor: pointer;
    }
  </style>

  <script>
    $script('/static/addons/badges/badge-popover.js');
  </script>

%endif

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
