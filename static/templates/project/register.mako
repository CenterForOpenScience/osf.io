<%inherit file="project.view.mako" />

<legend>Register</legend>

<script type="text/javascript">
	var Template = Ember.Application.create(${str('JSON.parse(\'' + form_values + '\')') if form_values else ''});
	var Templater = Ember.Application.create();
	Templater.Templates = Ember.Object.create({
		continueFlag:false,
		selectedTemplate:null,
		content:[${content}],
		submitRegistration:function(){
			jQuery.post(
                '${node_api_url}' + 'register/' + '${template_name if template_name else ''}/',
                { data: Template.getJson() },
                function(data){
                    if (data.status === 'success')
                        window.location = data.result;
                    else if (data.status === 'error')
                        window.location.reload();
                },
                'json'
            );
		},
		isContinue:function(){
			console.log(this.continueFlagCheck =='continue');
			if(this.continueFlagCheck =='continue'){
				this.set("continueFlag",true);
			}else{
				this.set("continueFlag",false);
			}
		}.observes('continueFlagCheck'),
		templateChange:function(){
			window.location = '${node_url}' + 'register/' + this.selectedTemplate.replace(/ /g, '_');
		}.observes('selectedTemplate'),
	});

	Ember.Handlebars.registerHelper('compare', function (lvalue, operator, rvalue, options) {

	    var operators, result;

	    if (arguments.length < 3) {
	        throw new Error("Handlerbars Helper 'compare' needs 2 parameters");
	    }

	    var lvalue = Ember.getPath(lvalue);

	    operators = {
	        '==': function (l, r) { return l == r; },
	        '===': function (l, r) { return l === r; },
	        '!=': function (l, r) { return l != r; },
	        '!==': function (l, r) { return l !== r; },
	        '<': function (l, r) { return l < r; },
	        '>': function (l, r) { return l > r; },
	        '<=': function (l, r) { return l <= r; },
	        '>=': function (l, r) { return l >= r; },
	        'typeof': function (l, r) { return typeof l == r; }
	    };

	    if (!operators[operator]) {
	        throw new Error("Handlerbars Helper 'compare' doesn't know the operator " + operator);
	    }

	    result = operators[operator](lvalue, rvalue);

	    if (result) {
	        return options.fn(this);
	    } else {
	        return options.inverse(this);
	    }

	});
</script>

<form class="form-horizontal">
	%if not template:
	<script type="text/x-handlebars">
		<div class="control-group">
		<label class="control-label">Registration Template</label>
		<div class="controls">
		{{view Ember.Select
	       contentBinding="Templater.Templates.content"
	       optionLabelPath="content"
	       optionValuePath="content"
	       selectionBinding="Templater.Templates.selectedTemplate"
	       prompt="Please Select"}}
	    </div>
		</div>
		<p>Registration will create a frozen version of the project as it exists right now.  You will still be able to make revisions to the project, but the frozen version will be read-only, have a unique url, and will always be associated with the project.</p>
		<p>Presently, registration options are open-ended.  If you wish to create a new registration template with additional detail, contact <a href="mailto:jspies@virginia.edu">Jeffrey Spies</a>.</p>
	</script>
	%endif

	<div id="registration_template">
		%if template:
			${template}
		%endif
	</div>
	%if template and not form_values:
		<script type="text/x-handlebars">
			<p>Registration cannot be undone, and the archived content and files cannot be deleted after registration. Please be sure the project is complete and comprehensive for what you wish to register.</p>
			<div class="control-group">
				<label class="control-label">Type "continue" if you are sure you want to continue</label>
				<div class="controls">
					{{view Ember.TextField valueBinding="Templater.Templates.continueFlagCheck"}}
				</div>
			</div>
			{{#if Templater.Templates.continueFlag}}
			<div class="control-group">
				<div class="controls">
				<button type="button" class="btn primary" onclick="Templater.Templates.submitRegistration()">Register</button>
				</div>
			</div>
			{{/if}}
		</script>
	%endif
</form>