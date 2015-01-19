<%inherit file="project/project_base.mako" />

<%def name="title()">${node['title']}</%def>
<div id="application" class="scripted">
    <div class="row">
        <div class="col-md-12">
            <form class="input-group" data-bind="submit: search">
                <input type="text" class="form-control" placeholder="Search" data-bind="value: query">
                <span class="input-group-btn">
                    <button class="btn btn-default" data-bind="click: search"><i class="icon-search"></i></button>
                </span>
            </form>
        </div>
    </div>
    <br/>
    <div class="row">
        <div class="col-md-6">
            <table class="table table-hover">
                <thead>
                    <tr>
                    </tr>
                </thead>
                <tbody data-bind="foreach: results">
                    <tr data-bind="click: $parent.setSelected.bind($data)">
                        <td>{{title | default:"No Title"}}</td>
                    </tr>
                </tbody>
            </table>
            <ul class="pagination" data-bind="visible: total() > 1">
                <li><a data-bind="click: pagePrev, visible: currentIndex() > 0">&laquo;</a></li>
                <li><a>{{currentIndex() + 1}}</a></li>
                <li><a data-bind="click: pageNext, visible: currentIndex() < total() " >&raquo;</a></li>
            </ul>
        </div>
        <div class="col-md-6">
            <pre data-bind="visible: results().length > 0">
                {{metadata}}
            </pre>
        </div>
    </div>
</div>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
<script src=${"/static/public/js/app/page.js" | webpack_asset}></script>
</%def>
## <script src=${"/static/public/vendor/jsonlint/formatter.js" | webpack_asset}></script>
