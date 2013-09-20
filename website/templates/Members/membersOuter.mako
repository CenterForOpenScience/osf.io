<%inherit file="contentContainer.mako" />

<div class="subnav">
    <ul class="nav nav-pills">
      <li><a href="/dashboard/">My Dashboard</a></li>
      <li><a href="/messages/">Messages</a></li>
      <li><a href="/profile/${user._primary_key}/">My Public Profile</a></li>
    </ul>
</div>

${next.body()}