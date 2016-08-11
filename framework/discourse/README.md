#Discourse Integration
[Discourse](http://discourse.org) is a modern open source forum software written in Ruby on Rails and Ember. This document describes how this branch integrates Discourse into the OSF as a more robust, extensible, and discoverable commenting and discussion system.

##Local Production Setup
Discourse can be run in either a production or a development environment. While working on changes to the OSF proper, the production environment would be more suitable since it runs fast inside docker container.

The general installation instructions can be found at https://github.com/discourse/discourse/blob/master/docs/INSTALL-cloud.md

The following instructions are specific to running Discourse from a Mac environment. Although Docker has more recently released a version that can run natively on Mac Os X, I only have experience so far with running it in a boot2docker virtualbox virtual machine.

###Get access to our target machine
Install Docker Toolbox and set up a default virtual machine. The default 1GB of ram should be enough for testing. The docker-machine command line tool should expose all the needed commands to manage the virtual machine.
Use `docker-machine ls` to determine the ip address of the virtual machine.
Use `docker-machine ssh` to ssh into the default machine.

Boot2Docker is by default missing some important utilities.
Run `tce-load -wi bash`, `tce-load -wi nano` (or make sure an editor you like is installed), and `export TERM=xterm`. You may want to put this last one in your ~/.bashrc file.

###Install Discourse
<pre>sudo -s
mkdir /var/discourse
git clone https://github.com/discourse/discourse_docker.git /var/discourse
cd /var/discourse</pre>

###Basic Configuration and Running Discourse
The files in /var/discourse/containers/ describe different Discourse configurations. Copy the app.yml file from this directory into that folder.

In app.yml use nano (or your favorite command line editor) to set `DISCOURSE_HOSTNAME` to the ip address of the virtual machine and `DISCOURSE_DEVELOPER_EMAILS` to your email address. It only needs to be a real email address if a real SMTP server is used.

The app.yml SMTP settings are intended for debugging with `python -m smtpd -n -c DebuggingServer localhost:387` running on the host machine. They should be changed in production to point to a real SMTP server. They assume the virtual machine sees the host machine at 10.0.2.2. This can be checked by running `route` in the virtual machine and checking the default gateway.

From /var/discourse run `./launcher rebuild app` to bootstrap and start the Discourse instance. This can also be used to update Discourse after changes are made in app.yml or the github repositories mentioned in it are changed.

If you get a complaint that port 80 is already in use, determine the PID of the offending process with `netstat -nlp` and kill it. I had this problem with a docker-proxy process. However, there only seemed to be interference on the initial bootstrap and not once actually running Discourse.

###More Configuration
Make sure that an SMTP server is setup, even if it is just with `python -m smtpd -n -c DebuggingServer localhost:387`.

Discourse should be accessible at port 80 of the ip address of the virtual machine. Navigate to the new Discourse instance and proceed to setup a new account using the email address previously specified in `DISCOURSE_DEVELOPER_EMAILS`. The password used doesn't really matter because we will configure Discourse for Single Sign On through the OSF.

Confirm the new account by navigating to the confirmation link which should appear in the python smtpd output. If the email setup doesn't work right away for you, it might be easier to use a script instead. From within the virtual machine run `./launcher enter app`, navigate to /var/www/discourse and then run `rake admin:create`. If it gives you trouble, you might need to prepend that with `RAILS_ENV=production bundle exec`. The script should leave you with a confirmed admin user.

Now logged in, click on the triple bar drop down in the top right corner and navigate to settings. Navigate to API settings and then create an All Users API key.

Open up your OSF website/settings/local.py file. Enter the API key we just created as the value for `DISCOURSE_API_KEY`. Also generate a random ~128 bit entropy string, for example with https://www.random.org/bytes/ and use this for `DISCOURSE_SSO_SECRET`. Also make sure that `DISCOURSE_SERVER_URL` points to your Discourse instance. Locally, this will be the ip address of virtual machine. You will also need to set the `contact_email` in the list of Discourse settings. This large list of settings can all be later changed from the admin interface in Discourse.

From the osf.io root directory run `python -m framework.discourse.configure`. This will set all the settings listed in local.py on the Discourse instance and perform a allow embedding of Discourse from the OSF. This is merely for convenience because all of these settings can be changed from within Discourse as well. Because these include SSO login settings, further sign-ons will occur through the OSF.

###Migrating Comments
The migration process consists of three scripts to run in sequence.

From the osf.io root directory run `python -m scripts.migration.migrate_to_discourse export_file`. This exports all the information about the OSF users, projects, and comments that need to be imported into Discourse. They are expected as a series of JSON objects, one per line.

Now we need to get that `export_file` into Discourse. Copy it into the virtual machine with `docker-machine scp export_file default:/home/docker`. We copy it to this home location because the docker user that scp uses does not necessarily have write permissions to /var/discourse.

From within the Discourse virtual machine, determine the docker container ID with `docker ps` and then copy the file into the docker container with `docker cp /home/docker/export_file 43e42ddbd963:/var/www/discourse`, substituting your container ID. Run `./launcher enter app` to enter into the docker container itself, navigate to /var/www/discourse and then run `RAILS_ENV=production bundle exec ruby script/import_scripts/osf.rb export_file return_file`. This import may take an hour or longer depending on the size of the export file. If it gets cancelled part way, subsequent runs will be able to skip over portions that have been already imported in.

The return_file contains various IDs and meta data about the entities imported into Discourse. In order for the OSF to be aware that Discourse has successfully imported these data, this file needs to be imported back into the OSF. Leaving the docker container, copy the file back out with `docker cp 43e42ddbd963:/var/www/discourse/return_file /home/docker`, and then exiting the virtual machine, copy the file back again with `docker-machine scp default:/home/docker/return_file ./`.

From the the osf.io directory run `python -m scripts.migration.migrate_from_discourse return_file` and the various Discourse IDs will be entered into the appropriate OSF objects.

Finally, if the import into Discourse makes mistakes. You can run `RAILS_ENV=production bundle exec ruby script/import_scripts/remove_all_imported.rb` before running the import script again to perform the import from scratch.

##Local Development Setup
If you want to actually work on the Discourse integration plugins and debug them, you need to be running Discourse in development mode. Discourse will run much slower like this, and will take more than a minute for a complete page refresh. However, javascript files will not be compressed, changes to css and js files will take effect on refresh, and changes to the ruby files will take effect just by restarting the rails server. In production mode, any of these changes would require a complete rebuild of the Discourse container.

Most of the steps listed above still apply, but there are some important differences.

The basic instructions for setup can be found at https://meta.discourse.org/t/beginners-guide-to-install-discourse-on-ubuntu-for-development/14727 . First follow those instructions to install Discourse with Vagrant. Pull the discourse git repo to someplace convenient for development. In this mode, I was not able to get SideKiq and email to work at all, so don't worry about them.

One of the great things about Vagrant is that it will mount your project directory inside of the virtual machine. This means, we don't have to bother with scp or cp to get files between the host machine and Discourse. To install the OSF integration plugins. Navigate to discourse/plugins and then run `git clone https://github.com/acshi/discourse-osf-plugin.git` and `git clone https://github.com/acshi/discourse-osf-projects.git`. If you plan on modifying these plugins (you probably are if you are bothering with the Development setup), first branch them yourself and then `git clone` your own branches.

Before trying out/starting up the new server (which will probably be at localhost:4000), you need to make an admin account. Run `vagrant ssh` from the discourse directory to enter your virtual machine. Navigate to /vagrant and then run `rake admin:create` and follow the prompts. You can startup the server from /vagrant by running `rails s -b 0.0.0.0`. If you want to manually test or modify the Discourse database you can run `rails c` to bring up a console with complete access to Discourse, but not the plugins.

You should now be able to log-in, create the admin API Key, and configure Discourse as detailed above. The migration process should be significantly simpler because you won't have to continually copy files between virtual machines and docker containers since your discourse development directory on the host is mounted in the virtual machine at /vagrant.

##Structure
There are three basic parts to the OSF/Discourse integration. Changes on the OSF directly, and then two Discourse plugins: discourse-osf-projects at https://github.com/acshi/discourse-osf-projects, and discourse-osf-plugin at https://github.com/acshi/discourse-osf-plugin.

###Changes to the OSF
The framework.discourse module provides a fairly thin wrapper around queries to the Discourse REST API. The majority of the methods operate on Project/File/Wiki nodes and synchronize information between the OSF and Discourse. It stores information in the OSF objects about the state of Discourse so that no more requests are made than necessary. The more interesting methods includes sync_project, which causes Discourse to make sure a forum for that project is setup with the correct name, contributors, and visibility permissions.

There are several hooks around different places in the OSF to create projects as needed and topics as needed: topics are created for a Project/File/Wiki when a page with a comment pane is requested.

Additionally, there is an API /v2/sso endpoint that is used to authenticate Discourse logins.

Finally, there is a “forum-feed” view for the main project page that displays the first several topics that would be seen by navigating to the forum page.

###Automatic Discourse Log-in and Log-out
In website/templates/nav.mako we add a section of javascript that keeps track of whether the user is logged in to Discourse. If the user is not logged in to the OSF, they must have been logged off of Discourse. And if they are logged in to the OSF but haven't yet been logged in to Discourse, we do this by inserting a hidden iframe that links to Discourse/session/sso. Although XSS protection and html headers prevent us from getting any information from this request and it fails to populate the iframe, it still effects the user's log-in to Discourse. We use localStorage to remember whether the user is logged in.

In framework.auth.views.auth_logout we add a hook to discourse.logout to log-out the user from Discourse by deleting their session key on the Discourse server.

###Syncing with Discourse
In website.project.model.Node.save we call discourse.sync_project to send changes in the project to Discourse, if any. This method will also create the forum in Discourse for the project if it hasn't been created yet.

In website.files.models.base, we copy all of the Discourse attributes between FileNode's and TrashedFileNode's. When a TrashedFileNode is restored, we call discourse.undelete_topic. When a FileNode is deleted, we call discourse.delete_topic. When a FileNode is saved, we call discourse.sync_topic to send changes, if any.

###The Comment Pane
Instead of showing comments from the OSF back-end and letting the user write new comments, we insert an embeddable iframe that shows a static view of the comments and provides a link to the full discourse topic page. More information about this process can be found at https://meta.discourse.org/t/embedding-discourse-comments-via-javascript/31963

In website.addons.base.views.addon_view_file we call discourse.get_or_create_topic_id(file_node) to get the relevant topic_id for the file and create one if we hadn't prior to now. We pass this value along with the DISCOURSE_SERVER_URL to the mako template file so that the embedded comment pane can be populated correctly.

The same is done in website.addons.wiki.views.project_wiki_view and website.project.views.node.\_view_project. In the last case, we also pass the value from discourse.get_user_apikey() as well so that the forum feed can be properly populated.

In website/static/js/commentpane.js, we add code to the toggle function so that the embedded comments are only loaded once the comment pane is opened. If the comment pane is closed and reopened, this refreshes the comments.

In the comment_pane_template.mako file, we replace most of the former comment code with a single div#discourse-comments with the Discourse host URL and topic id, which the javascript above will use to insert the embeddable iframe.

###Forum-feed component
This display is created by making an XHR request to Discourse using an API key specific to the logged-in user. We should be careful because this key could potentially be used to do anything on Discourse that the user has permissions to do.

The component is in website/static/js/components/forumfeed.js. We use the current user's API key to request Discourse/forum/:project_guid/latest.json, and then display just minimal information including title, project, and excerpt from the first 5 topics on the list. We make sure that all links are absolute and that usernames are replaced with full names.

In website/static/js/pages/project-dashboard-page.js we mount the forum-feed Mithril component and supply its parameters.

In website/templates/project/project.mako we take the Discourse url and API key passed to the mako template and save them in window.contextVars so they can be accessed by javascript.

##Further Work/Bugs to Fix
Apparently there is a better way to hook onto project changes that would be more targeted.

It seems that there are performance implications in calling save() more than absolutely necessary. The hooks around changes and in framework.discourse could be reworked to insure that only one call to save() is ever made.

If the Discourse server is down, this should minimally impact the rest of the OSF. Currently, exceptions raised will not be caught until they crash the requested page and display debugging information instead. While this helps with debugging, it would be inappropriate in a production environment.

Log Discourse errors correctly.

Since we seem to be using docstrings with Sphinx conventions, these could also be added to OSF code.

##Other Issues
Apparently the first page loads of Discourse in Development mode are only supposed to take 5-10 seconds (http://blog.discourse.org/2013/04/discourse-as-your-first-rails-app/), so I wonder why I have gotten so used to minute-long page loads. Funnily enough, it seems that during the majority of this time the rails server is idle.
