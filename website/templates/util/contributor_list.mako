<%def name="render_contributors()">
  <!-- ko foreach: contributors -->
    <!-- ko if: user_is_registered -->
    <a class="overflow"
        data-bind="attr: { href: user_profile_url, rel: 'tooltip', 'data-original-title': user_fullname }, text: user_display_name"></a>
    <span data-bind="text: separator"></span>
    <!-- /ko -->

    <!-- ko ifnot: user_is_registered -->
    <span class="overflow" data-bind="text: user_display_name"></span>
    <span data-bind="text: separator"></span>
    <!-- /ko -->

    <!-- ko if: $parent.others_count() && $index() === $parent.contributors().length - 1 -->
    <!-- Assuming node_url is a property of the parent context -->
    <a data-bind="attr: {href: $parent.nodeUrl}, text: $parent.others_count() + ' more'"></a>
    <!-- /ko -->
  <!-- /ko -->
</%def>

<%def name="render_contributors_full()">
  <!-- ko foreach: {data: contributors, afterRender: afterRender} -->
  <li data-bind="attr: { 'data-pk': id }, 
                  css: { 'contributor': true, 
                          'contributor-registered': registered, 
                          'contributor-unregistered': !registered, 
                          'contributor-self': $parent.user.id == id }">
      <!-- ko if: registered -->
      <a class="overflow"
          data-bind="attr: { rel: is_condensed ? 'tooltip' : '', href: url, title: fullname }, 
                    text: condensedFullname"></a>
      <!-- /ko -->
      <!-- ko ifnot: registered -->
      <span class="overflow"
          data-bind="attr: { rel: is_condensed ? 'tooltip' : '', title: fullname }, 
                    text: condensedFullname"></span>
      <!-- /ko -->
  </li>
  <!-- /ko -->
</%def>
