<!-- Import Knockout -->
<script src="//cdnjs.cloudflare.com/ajax/libs/knockout/2.3.0/knockout-min.js"></script>

<script type="text/javascript">

    var stringTemplateSource = function (template) {
        this.template = template;
    };

    stringTemplateSource.prototype.text = function () {
        return this.template;
    };

    var stringTemplateEngine = new ko.nativeTemplateEngine();
    stringTemplateEngine.makeTemplateSource = function (template) {
        return new stringTemplateSource(template);
    };

    var templates = {
        textarea: '<textarea data-bind="value:value, attr:{name:id}, disable:disable"></textarea>',
        textfield: '<input type="text" data-bind="value:value, attr:{name:id}, disable:disable" />',
        select: '<select data-bind="options: options, value:value, attr:{name:id}, optionsCaption: caption, disable:disable"></select>',
        checkbox: '<input type="checkbox" data-bind="checked:value, attr:{name:id}, disable:disable" />'
    };

    ko.bindingHandlers.item = {
        init: function(element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) {
            var options = ko.utils.unwrapObservable(valueAccessor());
            options.value = options.value || '';
            options.disable = !!options.value;
            ko.renderTemplate(templates[options.type], options, { templateEngine: stringTemplateEngine }, element, 'replaceNode');
        }
    };

    function ViewModel(schema) {
        var self = this;
        self.schema = schema;
        self.continueText = ko.observable('');
        self.continueFlag = ko.computed(function() {
            return self.continueText() === 'continue';
        });
    }

</script>
