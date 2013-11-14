
<style>

##    .repeat-section {
##        margin-bottom: 25px;
##        margin-left: 25px;
##        border: 1px;
##        border-style: solid;
##    }
##
##    .repeat-subsection {
##        background: grey;
##        margin-bottom: 15px;
##        margin-left: 25px;
##    }

    .required {
        color: red;
    }

</style>

##<!-- Load schema data -->
##<script src="/modular-meta-data/schema.js"></script>

<!-- Load libraries -->

##<link rel="stylesheet" href="/modular-meta-data/assets/css/bootstrap.min.css" />

##<script src="/modular-meta-data/assets/js/knockout-3.0.0.js"></script>
##<script src="/modular-meta-data/assets/js/jquery-1.10.2.min.js"></script>

<!-- Section template -->
<script id="section" type="text/html">
    <h2 data-bind="text:title"></h2>
    <div data-bind="foreach:contents">
        <div class="content" data-bind="css:{'repeat-section':$data.repeatSection, 'repeat-subsection':$parent.repeatSection}">
            <div data-bind="template:{name:$root.getTemplate($data), if:$data.visible()}"></div>
            <div data-bind="if:$root.canRemove($data)">
                <a class="btn" data-bind="click:$data.removeRepeat">Remove</a>
            </div>
        </div>
    </div>
    <div data-bind="if:$root.canAdd($data)">
        <a class="btn" data-bind="click:function(){addRepeat(null, true)}">Add</a>
    </div>
</script>

<!-- Item container template -->
<script id="item" type="text/html">
    <div class="control-group">
        <label class="control-label" data-bind="css:{required:required}">
            <span data-bind="if:required">* </span>
            <span data-bind="text:label, attr:{for:id}"></span>
        </label>
        <div class="controls">
            <span class="help-block" data-bind="text:helpText"></span>
            <div data-bind='item:$data, attr:{id:id}'></div>
            <div data-bind="text:validateText"></div>
        </div>
    </div>
</script>

<!-- Item templates -->
<script id="textfield" type="text/html">
    <input type="text" data-bind="value:value, valueUpdate:'onblur', attr:{name:id, id:id}, disable:disable || $root.disable" />
</script>
<script id="textarea" type="text/html">
    <textarea data-bind="value:value, valueUpdate:'onblur', attr:{name:id, id:id}, disable:disable || $root.disable"></textarea>
</script>
<script id="select" type="text/html">
    <select data-bind="options: options, value:value, attr:{name:id, id:id, multiple:multiple}, optionsCaption:caption, disable:disable || $root.disable"></select>
</script>
<script id="radio" type="text/html">
    <div data-bind="foreach:options">
        <div>
            <input type="radio" data-bind="value:$data, checked:$parent.value, disable:$parent.disable || $root.disable" />
            <span data-bind="text:$data"></span>
        </div>
    </div>
</script>
<script id="checkbox" type="text/html">
    <div data-bind="foreach:options">
        <div>
            <input type="checkbox" data-bind="value:$data, checked:$parent.value, disable:$parent.disable || $root.disable" />
            <span data-bind="text:$data"></span>
        </div>
    </div>
</script>
<script id="file" type="text/html">
    <select data-bind="value:node, options:nodes, optionsCaption:caption, disable:disable || $root.disable"></select>
    <select data-bind="visible:files, value:value, options:files, optionsCaption:caption, disable:disable || $root.disable"></select>
</script>

<div id="meta-data-container">

    <form data-bind="with:currentPage">
        <div data-bind="template:{name:'section', data:$data}"></div>
    </form>

    <hr />

    <!-- Pagination -->
    <div data-bind="if:npages > 1">
        <div class="control-group">
            <div class="controls">
                <button class="btn" data-bind="click:previous, disable:isFirst">Previous</button>
                <span class="progress-meter" style="padding: 0px 10px 0px 10px;">
                    Page <span data-bind="text:currentIndex() + 1"></span>
                    of <span data-bind="text:npages"></span>
                </span>
                <button class="btn" data-bind="click:next, disable:isLast">Next</button>
            </div>
        </div>
    </div>

    <hr />

##    <!-- Submission -->
##    <div class="control-group">
##        <div class="controls">
##            <input type="submit" value="Submit" class="btn" data-bind="click:submit" />
##            <a class="btn comment-cancel">Cancel</a>
##        </div>
##    </div>

</div>

##<!-- Apply Knockout bindings -->
##<script type="text/javascript">
##
##    var viewModel = new MetaData.ViewModel(schema);
##    ko.applyBindings(
##        viewModel,
##        document.getElementById('meta-data-container')
##    );
##
##    // Update
##    viewModel.updateIdx();
##
##</script>