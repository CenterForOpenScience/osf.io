<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>

<div class="subnav">
    <ul class="nav nav-pills">
      <li><a href="/dashboard/">My Dashboard</a></li>
      <li><a href="/messages/">Messages</a></li>
      <li><a href="/profile/${user_id}/">My Public Profile</a></li>
    </ul>
</div>

${next.body()}

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>
