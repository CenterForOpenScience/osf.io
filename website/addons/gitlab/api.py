import gitlab
import settings as gitlab_settings

client = gitlab.Gitlab(gitlab_settings.HOST, token=gitlab_settings.TOKEN)
