"""

"""

from framework import fields
from website.addons.base import AddonNodeSettingsBase, AddonUserSettingsBase

from .api import Figshare
from . import settings as figshare_settings

class AddonFigShareUserSettings(AddonUserSettingsBase):

    oauth_request_token = fields.StringField()
    oauth_request_token_secret = fields.StringField()
    oauth_access_token = fields.StringField()
    oauth_access_token_secret = fields.StringField()    

    @property
    def has_auth(self):
        return self.oauth_access_token is not None

    def to_json(self, user):
        rv = super(AddonFigShareUserSettings, self).to_json(user)
        rv.update({
            'authorized': self.has_auth,
        })
        return rv

class AddonFigShareNodeSettings(AddonNodeSettingsBase):
    figshare_id = fields.StringField()
    figshare_type = fields.StringField()
    api_url = fields.StringField()

    user_settings = fields.ForeignField(       
        'addonfigshareusersettings', backref='authorized'
    )
    
    registration_data = fields.DictionaryField()

    @property
    def embed_url(self):
        return 'http://wl.figshare.com/articles/{fid}/embed?show_title=1'.format(
            fid=self.figshare_id,
        )

    def to_json(self, user):
        figshare_user = user.get_addon('figshare')
        rv = super(AddonFigShareNodeSettings, self).to_json(user)
        rv.update({
            'figshare_id': self.figshare_id or '',
            'figshare_type': self.figshare_type or '',
            'has_user_authorization': figshare_user and figshare_user.has_auth,
            'figshare_options': []
        })
        figshare_options = []
        settings = self.user_settings
        if settings and settings.has_auth:            
            connect = Figshare.from_settings(self.user_settings)
            figshare_options = connect.get_options()
            rv.update({
                'authorized_user': self.user_settings.owner.fullname,
                'disabled': user != self.user_settings.owner,
                'figshare_options': figshare_options
            })    
        return rv
    
    #############
    # Callbacks #
    #############
    def before_page_load(self, node, user):
        """

        :param Node node:
        :param User user:
        :return str: Alert message

        """

        messages = [
            'The FigShare add-on page has been combined with the pre-existing '
            'Files page, which also now includes files from your other add-ons. '
            'To work with the files in your FigShare add-on, browse to the '
            '<a href="{0}">Files</a> page.'.format(
                node.url + 'files/'
            )
        ]

        # Quit if not contributor
        if not node.is_contributor(user):
            return messages

        # Quit if not configured
        if self.figshare_id is None:
            return messages

        figshare = node.get_addon('figshare')
        # Quit if no user authorization
        if self.user_settings is None:
            figshare.api_url = figshare_settings.API_URL
        else:
            figshare.api_url = figshare_settings.API_OAUTH_URL
        figshare.save()    

        node_permissions = 'public' if node.is_public else 'private'

        if figshare.figshare_type == 'project' and node_permissions == 'private':
            message = (
                'Warnings: This OSF {category} is private but FigShare project {project} may contain some public files or filesets'.format(category=node.project_or_component,
                             project=figshare.figshare_id)
                                                                                                                                    )
            messages.append(message)
            return messages
            
        connect = Figshare.from_settings(self.user_settings)
        article_is_public = connect.article_is_public(self.figshare_id)        
        
        article_permissions = 'public' if article_is_public else 'private'

        if article_permissions != node_permissions:
            message = (
                'Warnings: This OSF {category} is {node_perm}, but the FigShare '
                '{node} {article} is {article_perm}. '.format(
                    category=node.project_or_component,
                    node_perm=node_permissions,
                    article_perm=article_permissions,                   
                    article=self.figshare_id,
                    node=self.figshare_type
                )
            )
            if article_permissions == 'private':
                message += (
                    'Users can view the contents of this private FigShare '
                    'article through this public project.'
                )
            messages.append(message)
            return messages

    def before_remove_contributor(self, node, removed):
        """
        
        :param Node node:
        :param User removed:
        :return str: Alert message
        
        """
        if self.user_settings and self.user_settings.owner == removed:
            return (
                'The FigShare add-on for this {category} is authenticated '
                'by {user}. Removing this user will also remove write access '
                'to the article unless another contributor re-authenticates. '
                ).format(
                category=node.project_or_component,
                user=removed.fullname,                
                )
            
    def after_remove_contributor(self, node, removed):
        """
            
        :param Node node:
        :param User removed:
        :return str: Alert message
        
        """
        if self.user_settings and self.user_settings.owner == removed:
            
            # Delete OAuth tokens
            self.user_settings = None
            self.api_url = figshare_settings.API_URL 
            self.save()
            
            return (
                'Because the FigShare add-on for this project was authenticated '
                'by {user}, authentication information has been deleted. You '
                'can re-authenticate on the <a href="{url}settings/">'
                'Settings</a> page.'.format(
                    user=removed.fullname,
                    url=node.url,
                    )
                )
        
    def before_fork(self, node, user):
        """
        
        :param Node node:
        :param User user:
        :return str: Alert message
        
        """
        if self.user_settings and self.user_settings.owner == user:
            return (
                'Because you have authenticated the FigShare add-on for this '
                '{cat}, forking it will also transfer your authorization to '
                'the forked {cat}.'
                ).format(
                cat=node.project_or_component,
                )
        return (
            'Because this FigShare add-on has been authenticated by a different '
            'user, forking it will not transfer authentication to the forked '
            '{cat}.'
            ).format(
            cat=node.project_or_component,
            )
    
    def after_fork(self, node, fork, user, save=True):
        """
        
        :param Node node: Original node
        :param Node fork: Forked node
        :param User user: User creating fork
        :param bool save: Save settings after callback
        :return tuple: Tuple of cloned settings and alert message
        
        """
        clone, _ = super(AddonFigShareNodeSettings, self).after_fork(
            node, fork, user, save=False
            )
        
        # Copy authentication if authenticated by forking user
        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = (
                'FigShare authorization copied to forked {cat}.'
                ).format(
                cat=fork.project_or_component,
                )
        else:
            message = (
                'FigShare authorization not copied to forked {cat}. You may '
                'authorize this fork on the <a href={url}>Settings</a> '
                'page.'
                ).format(
                cat=fork.project_or_component,
                url=fork.url + 'settings/'
                )
                
        if save:
            clone.save()
                            
        return clone, message

    def before_register(self, node, user):
        """
        
        :param Node node:
        :param User user:
        :return str: Alert message
        
        """
        if self.user_settings:
            return (
                'Registering this {cat} will copy the authentication for its '
                'FigShare add-on to the registered {cat}.'
                ).format(
                cat=node.project_or_component,
                )
        
    def after_register(self, node, registration, user, save=True):
        """
        
        :param Node node: Original node
        :param Node registration: Registered node
        :param User user: User creating registration
        
        :return tuple: Tuple of cloned settings and alert message
        
        """
        clone, message = super(AddonFigShareNodeSettings, self).after_register(
            node, registration, user, save=False
            )
                
        # Copy foreign fields from current add-on
        clone.user_settings = self.user_settings
                
        # TODO handle registration
                


        if save:
            clone.save()

        return clone, message

                
