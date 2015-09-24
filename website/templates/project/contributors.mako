<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Contributors</%def>

<%include file="project/modal_generate_private_link.mako"/>
<%include file="project/modal_add_contributor.mako"/>

<div class="page-header  visible-xs">
  <h2 class="text-300">Contributors</h2>
</div>

<div class="row">
    <div class="col-lg-10 col-lg-offset-1">
        <div class="col-lg-6">
            <div id="manageContributors" class="scripted">
                <h3> Contributors
                    <!-- ko if: canEdit -->
                        <a href="#addContributors" data-toggle="modal" class="btn btn-success btn-sm" style="margin-left:20px;margin-top: -3px">
                          <i class="fa fa-plus"></i> Add
                        </a>
                    <!-- /ko -->
                    <span>
                        <i class="fa fa-search"></i>
                    </span>
                    <input type="text" class="searchable"/>
                    <div class="btn-group" role="group" class="filtergroup">
                        <button id="admin-filter-btn" type="button" class="btn btn-default filter-btn">Admins</button>
                        <button id="write-filter-btn" type="button" class="btn btn-default filter-btn">Read + Write</button>
                        <button id="read-filter-btn" type="button" class="btn btn-default filter-btn">Read</button>
                    </div>

                </h3>
                % if 'admin' in user['permissions'] and not node['is_registration']:
                    <p>Drag and drop contributors to change listing order.</p>
                % endif
                <div id='contributors' class="row collapse-container" data-bind="template: {
                            name: 'contribCard',
                            foreach: contributors,
                            as: 'contributor',
                            isEnabled: canEdit,
                            options: {
                              containment: '#manageContributors'
                            }
                        }">
                    </div>
                <div data-bind="if: adminContributors.length">
                    <h4>
                        Admins on Parent Projects
                        <i class="fa fa-question-circle admin-info"
                              data-content="These users are not contributors on
                              this component but can view and register it because they
                                are administrators on a parent project."
                              data-toggle="popover"
                              data-title="Admins on Parent Projects"
                              data-container="body"
                              data-placement="right"
                              data-html="true"
                        ></i>
                    </h4>
                    <div id='adminContributors' class="row" aria-multiselectable="true" data-bind="template: {
                            name: 'contribCard',
                            foreach: adminContributors,
                            as: 'contributor'
                        }">
                    </div>
                </div>
                ${buttonGroup()}
            </div>
        </div>

        <div class="col-lg-6">
            % if 'admin' in user['permissions']:
                <h3>View-only Links
                    <a href="#addPrivateLink" data-toggle="modal" class="btn btn-success btn-sm" style="margin-left:20px;margin-top: -3px">
                      <i class="fa fa-plus"></i> Add
                    </a>
                </h3>
                <p>Create a link to share this project so those who have the link can view&mdash;but not edit&mdash;the project.</p>
                <div class="scripted" id="linkScope">
                    <div class="row" aria-multiselectable="true"            data-bind="template:
                                    {name: 'linkCard',
                                    foreach: privateLinks,
                                    afterRender: afterRenderLink}">
                    </div>
                </div>
            % endif
        </div>
    </div>
</div>

<link rel="stylesheet" href="/static/css/pages/contributor-page.css">

<script id="linkCard" type="text/html">
    <div data-bind="attr: {class: classes}">
        <div class="panel panel-default">
            <div class="panel-heading" data-bind="attr: {id: 'linkHeading' + $index(), href: '#linkCard' + $index()}" role="button" data-toggle="collapse" aria-expanded="false" aria-controls="card" onclick="toggleIcon(this)">
                <button onclick="cancelProp(event)" style="vertical-align: top;" title="Copy to clipboard" class="btn btn-default btn-sm" data-bind="attr: {data-clipboard-text: linkUrl}" >
                    <i class="fa fa-copy"></i>
                </button>
                <span class="header-content">
                    <span class="link-name m-b-xs" data-bind="text: name, tooltip: {title: 'Link name'}"></span>
                    <a onclick="cancelProp(event)" style="display: block; font-style: italic; font-size: 75%;" data-bind="attr: {href: linkUrl}, text: linkUrl"></a>
                </span>
                <div class="pull-right">
                    <i class="fa fa-angle-down toggle-icon"></i>
                </div>

            </div>
            <div data-bind="attr: {id: 'linkCard' + $index()}" class="panel-collapse collapse" data-bind="attr: {aria-labelledby: 'linkHeading' + $index()}">
                <div class="panel-body">
                    <span style="display: block"><h5>Shares</h5></span>
                    <ul class="private-link-list narrow-list" data-bind="foreach: nodesList">
                       <li data-bind="style:{marginLeft: $data.scale}">
                          <span data-bind="getIcon: $data.category"></span>
                          <a data-bind="text:$data.title, attr: {href: $data.url}"></a>
                       </li>
                    </ul>
                    <span style="display: block"><h5>Created on</h5></span>
                    <span class="link-create-date" data-bind="text: dateCreated.local, tooltip: {title: dateCreated.utc}"></span>
                    <span style="display: block"><h5>Created by</h5></span>
                        <a data-bind="text: creator.fullname, attr: {href: creator.url}" class="overflow-block" style="width: 300px"></a>
                    <span style="display: block"><h5>Anonymous</h5></span>
                    <span style="display: block" data-bind="html: anonymousDisplay"></span>
                    <!-- ko if: $root.nodeIsPublic && anonymous -->
                        <i data-bind="tooltip: {title: 'Public projects are not anonymized.'}" class="fa fa-question-circle fa-sm"></i>
                    <!-- /ko -->
                    <button style="display: block" type="button" class="btn btn-danger" data-bind="click: $root.removeLink, tooltip: {title: removeLink}">
                        Remove
                    </button>
                </div>
            </div>
        </div>
    </div>
</script>

<script id="contribCard" type="text/html">
    <div data-bind="attr: {class: classes}"
         data-bind="click: unremove, css: {'contributor-delete-staged': deleteStaged}">
        <div class="panel panel-default">
            <div class="panel-heading" data-bind="attr: {id: type() + 'Heading' + $index(), href: '#' + type() + 'Card' + $index()}" role="button" data-toggle="collapse" aria-expanded="false" aria-controls="card" onclick="toggleIcon(this)">
                <img style='vertical-align: top' data-bind="attr: {src: contributor.gravatar_url}" />
                <span class="header-content">
                    <span data-bind="ifnot: profileUrl">
                        <span data-bind="text: contributor.shortname"></span>
                    </span>
                    <span data-bind="if: profileUrl">
                        <a onclick="cancelProp(event)" class="no-sort search" data-bind="text: contributor.shortname, attr:{href: profileUrl}"></a>
                    </span>
                    <span style="display: block" data-bind="text: curPermission().text + visibleText()"></span>
                </span>
                <div class="pull-right">
                    <i class="fa fa-angle-down toggle-icon"></i>
                </div>
            </div>
            <div data-bind="attr: {id: type() + 'Card' + $index()}" class="panel-collapse collapse" data-bind="attr: {aria-labelledby: type() + 'Heading' + $index()}">
                <div class="panel-body">
                    <!-- ko if: contributor.canEdit() -->
                        <h5 style="display: block">Permissions</h5>
                        <span style="display: none" data-bind="text: curPermission().text" class="permission-search"></span>
                        <span style="display: block" data-bind="visible: notDeleteStaged">
                            <select class="form-control input-sm" data-bind="
                                options: permissionList,
                                value: curPermission,
                                optionsText: 'text',
                                style: { font-weight: change() ? 'normal' : 'bold' }, attr: {name : curPermission}"
                            >
                            </select>
                        </span>
                        <span style="display: block" data-bind="visible: deleteStaged">
                            <span data-bind="text: formatPermission"></span>
                        </span>
                    <!-- /ko -->
                    <!-- ko ifnot: contributor.canEdit() -->
                        <span style="display: block" data-bind="text: formatPermission"></span>
                    <!-- /ko -->
                    <h5 style="display: block" >Bibliographic Contributor</h5>
                    <span style="display: block">
                        <input
                                type="checkbox" class="no-sort biblio"
                                data-bind="checked: visible, enable: $parent.canEdit() && !contributor.isAdmin"
                            />
                    </span>
                    <!-- ko if: contributor.canEdit() -->
                        <!-- ko ifnot: deleteStaged -->
                            <!-- Note: Prevent clickBubble so that removing a
                                contributor does not immediately un-remove her. -->
                            <span style="display: block">
                                <a data-bind="click: remove, clickBubble: false, tooltip: {title: 'Remove contributor'}">
                                    <button type="button" class="btn btn-danger">Remove</button>
                                </a>
                            </span>
                        <!-- /ko -->
                        <!-- ko if: deleteStaged -->
                            Save to Remove
                        <!-- /ko -->
                    <!-- /ko -->

                    <!-- ko ifnot: contributor.canEdit() -->
                        <!-- ko if: canRemove -->
                            <span style="display: block">
                                <a data-bind="click: function() { $data.removeSelf($parent)}, tooltip: {title: 'Remove contributor'}">
                                    <button type="button" class="btn btn-danger">Remove</button>
                                </a>
                            </span>
                        <!-- /ko -->
                    <!-- /ko -->
##                     <span style="display: block" data-bind="text: isAdmin"></span>
                </div>
            </div>
        </div>
    </div>
</script>


<%def name="buttonGroup()">
    % if 'admin' in user['permissions']:
        <a class="btn btn-danger contrib-button" data-bind="click: cancel, visible: changed">Discard Changes</a>
        <a class="btn btn-success contrib-button" data-bind="click: submit, visible: canSubmit">Save Changes</a>
        <br /><br />
    % endif
        <div data-bind="foreach: messages">
            <div data-bind="css: cssClass">{{ text }}</div>
        </div>
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}

    <script type="text/javascript">
      window.contextVars = window.contextVars || {};
      window.contextVars.user = ${ user | sjson, n };
      window.contextVars.isRegistration = ${ node['is_registration'] | sjson, n };
      window.contextVars.contributors = ${ contributors | sjson, n };
      window.contextVars.adminContributors = ${ adminContributors | sjson, n };

    </script>

    <script type="text/javascript">
        function toggleIcon(el) {
            jQuery(el.querySelector("i.toggle-icon")).toggleClass("fa-angle-down fa-angle-up");
        }
    </script>
    <script src=${"/static/public/js/sharing-page.js" | webpack_asset}></script>

    <script type="text/javascript">

        function cancelProp(e) {
            e.cancelBubble = true;
            if (e.stopPropagation) {
                e.stopPropagation();
            }
        }
        (function($){
            $.fn.filtergroup = function (options) {
                var settings = $.extend({
                    items: '.items',
                    fade: 'true',
                    buttons: [],
                    buttonClass: '.filter-btn',
                    inputs: []
                }, options);

                var active = [];

                var fade = function(list){


                    if(action == 'on' ){
                        if(settings.fade){
                            element.fadeIn();
                        } else {
                            element.show();
                        }
                    }
                    if(action == 'off'){
                        if(settings.fade){
                            element.fadeOut();
                        } else {
                            element.hide();
                        }
                    }

                };

                jQuery(settings.buttonClass).on('click', function () {
                    $(this).toggleClass('active');
                    if ($(this).hasClass('active')) {
                        active.push(this.id);
                    } else {
                        active.splice(active.indexOf(this.id), 1);
                    }

                    console.log("filter: name = " + $(settings.inputs[0].input).val() + " buttons: " + active);
                });


##                 var el, content;
##                             $(settings.items).each(function () {
##                                 el = this.querySelector(settings.selector);
##                                 content = jQuery(el).text();
##                                 if (content === settings.match) {
##                                     fade($(this), 'on');
##                                 } else {
##                                     fade($(this), 'off');
##                                 }
##                             });




            }
        }(jQuery));

        (function($) {
            $.fn.searchable = function (options) {
                return this.keyup(function () {
                    var text, el, content, exists;
                    text = $(this).val().toLowerCase();
                    if (text.length >= 0) {
                        $(settings.items).each(function () {
                            el = this.querySelector(settings.selector);
                            content = jQuery(el).text().toLowerCase();
                            exists = content.indexOf(text);
                            if (exists != -1) {
                                fade($(this), 'on');
                            } else {
                                fade($(this), 'off');
                            }
                        });

                    }
                });
            }
        }(jQuery));

        $('.filtergroup').filtergroup({
            buttons: [
                {
                    selector: '.permission-filter',
                    match: "Administrator"
                }, {
                    selector: '.permission-filter',
                    match: "Read + Write"
                }, {
                    selector: '.permission-filter',
                    match: "Read"
                }
            ],
            inputs: [
                {
                    selector: '.search',
                    input: '.searchable'
                }
            ]
        })
</script>


</%def>
