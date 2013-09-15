<%inherit file="project.view.mako" />

<% import os %>

<legend>Register</legend>

<script type="text/javascript">
	var Template = Ember.Application.create(${str('JSON.parse(\'' + form_values + '\')') if form_values else ''});
	var Templater = Ember.Application.create();
	Templater.Templates = Ember.Object.create({
		continueFlag:false,
		selectedTemplate:null,
		content:[
			${','.join([str('"' + i.replace('.txt', '').replace('_', ' ') + '"') for i in os.listdir('website/static/registration_templates/')])}
		],
		submitRegistration:function(){
			jQuery.post(
                    window.location,
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
			window.location = nodeToUseUrl() + '/register/' + this.selectedTemplate.replace(/ /g, '_');
			##$.ajax({
			##	url:'/',
			##	cache:false,
			##	success:function(data){
			##		$(data).filter('script[type="text/x-handlebars"]').each(function() {
			##		## 	console.log(template);
    		##		##	##Ember.TEMPLATES["dynamic"] = ;
    		##		##
    		##			console.log($(this).html());
    		##			template = Ember.Handlebars.compile($(this).html());
    		##			Ember.TEMPLATES["login_view"] = template;
    		##			console.log(template(Ember));
    		##			$("#registration_template").html(template(Ember));
  			##		});
			##		
			##	}
			##});
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

	##<div class="control-group">
	##<label class="control-label">Name</label>
	##<div class="controls">
	##	{{view Ember.TextField valueBinding="Templater.query"}}
	##</div>
	##{{ Templater.query }}
	##</div>
					
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

## 

##<legend>Register</legend>
##<div class="register" id="1">
##	<label>Registration cannot be undone, and the archived content and files cannot be deleted after registration, are you sure that you wish to proceed?</label>
##	<label class="radio">
##  	<input type="radio" name="optionsRadios" id="optionsRadios1" value="option1">
##  	Yes
##	</label>
##	<label class="radio">
##	  <input type="radio" name="optionsRadios" id="optionsRadios2" value="option2">
##	  No
##	</label>
##</div>
##<br />
##<div class="register" id="2">
##	<label>Is this project complete and comprehensive for what you wish to register?  You cannot undo, or repeat a confirmatory registration. </label> 
##
##	<label class="radio">
##  	<input type="radio" name="optionsRadios" id="optionsRadios1" value="option1">
##  	Yes
##	</label>
##	<label class="radio">
##	  <input type="radio" name="optionsRadios" id="optionsRadios2" value="option2">
##	  No
##	</label>
##</div>
##<br />
##<div class="register" id="2">
##	<label>Is data collection for this project underway or complete? </label>
##
##	<label class="radio">
##  	<input type="radio" name="optionsRadios" id="optionsRadios1" value="option1">
##  	Yes. Some or all of the data exists
##	</label>
##	<label class="radio">
##	  <input type="radio" name="optionsRadios" id="optionsRadios2" value="option2">
##	  No. No data exists for this project
##	</label>
##	<label>
##		<textarea style="width:600px;" placeholder="Provide any relevant explanatory information"></textarea>
##		
##	</label>
##</div>
##<br />
##<div class="register" id="2">
##	<label>Has anyone looked at the datafile(s)?</label>
##
##	<label class="radio">
##  	<input type="radio" name="optionsRadios" id="optionsRadios1" value="option1">
##  	No. No data exists for this project
##	</label>
##	<label class="radio">
##	  <input type="radio" name="optionsRadios" id="optionsRadios2" value="option2">
##	  Yes.
##	</label>
##	<label>
##		<textarea style="width:600px;" placeholder="Provide any relevant explanatory information"></textarea>
##		
##	</label>
##</div>
##<br />
##<div class="register" id="2">
##	<label>Has anyone touched the datafile(s)?</label>
##
##	<label class="radio">
##  	<input type="radio" name="optionsRadios" id="optionsRadios1" value="option1">
##  	No, the data have not been touched.
##	</label>
##	<label class="radio">
##	  <input type="radio" name="optionsRadios" id="optionsRadios2" value="option2">
##	  Yes, someone has opened or examined the datafile.
##	</label>
##	<label>
##		<textarea style="width:600px;" placeholder="Provide any relevant explanatory information"></textarea>
##	</label>
##</div>
##<br />
##<div class="register" id="2">
##	<label>Has anyone touched the datafile(s)?</label>
##
##	<label class="radio">
##  	<input type="radio" name="optionsRadios" id="optionsRadios1" value="option1">
##  	No, the data have not been touched.
##	</label>
##	<label class="radio">
##	  <input type="radio" name="optionsRadios" id="optionsRadios2" value="option2">
##	  Yes, someone has opened or examined the datafile.
##	</label>
##	<label>
##		<textarea style="width:600px;" placeholder="Provide any relevant explanatory information"></textarea>
##	</label>
##</div>
##<br />
##<p>You have confirmed that all of the content, files, and components are in the project and prepared to be registered according to your intentions.  Registering the project cannot be undone.##  Once registered, that registered archive cannot be edited or deleted.  Once registered, the project and components will be time and date stamped, and your responses to this registration ##questionnaire will be associated with your project.  Click "Register" below to continue.</p>
##
##<form method="post">
##	<button type="submit" class="btn primary">Register</button>
##</form>