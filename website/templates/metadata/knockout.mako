## TODO: Is this file used anywhere?

## TODO: Put this is site.js
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
        textarea: '<textarea class="form-control" data-bind="value:value, attr:{name:id}, disable:disable"></textarea>',
        textfield: '<input class="form-control" type="text" data-bind="value:value, attr:{name:id}, disable:disable" />',
        select: '<select class="form-control" data-bind="options: options, value:value, attr:{name:id}, optionsCaption: caption, disable:disable"></select>',
        checkbox: '<input class="form-control" type="checkbox" data-bind="checked:value, attr:{name:id}, disable:disable" />'
    };

    ko.bindingHandlers.item = {
        init: function(element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) {
            var options = ko.utils.unwrapObservable(valueAccessor());
            options.value = options.value || '';
            options.disable = options.diable || bindingContext.$root.disable;
            ko.renderTemplate(templates[options.type], options, { templateEngine: stringTemplateEngine }, element, 'replaceNode');
        }
    };

    function Page(id, title, questions) {
        this.id = ko.observable(id);
        this.title = title;
        this.questions = questions;
    }

    function ViewModel(schema, disable) {

        var self = this;

        var pages;
        if ('pages' in schema) {
            pages = schema.pages;
        } else {
            pages = [
                {
                    id: 1,
                    title: '',
                    questions: schema.questions
                }
            ]
        }

        self.npages = pages.length;
        self.pages = ko.observableArray(
            ko.utils.arrayMap(pages, function(page) {
                return new Page(page.id, page.title, page.questions);
            })
        );

        self.currentIndex = ko.observable(0);
        self.currentPage =  ko.computed(function(){
           return self.pages()[self.currentIndex()];
        });
        self.previous = function() {
            self.currentIndex(self.currentIndex()-1);
        };
        self.next = function() {
            self.currentIndex(self.currentIndex()+1);
        };
        self.isFirst = function() {
            return self.currentIndex() === 0;
        };
        self.isLast = function() {
            return self.currentIndex() === self.npages - 1;
        };

        self.disable = disable || false;

        self.continueText = ko.observable('');
        self.continueFlag = ko.computed(function() {
            return self.continueText() === 'continue';
        });

    }

</script>
