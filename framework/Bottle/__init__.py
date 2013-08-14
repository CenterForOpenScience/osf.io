import bottle

from bottle import route
from bottle import get
from bottle import post

from bottle import request
from bottle import response
from bottle import redirect
from bottle import app
from bottle import run
from bottle import static_file
from bottle import debug
from bottle import abort

app = bottle.default_app()
app.catchall=False

def getReferrer():
    return request.environ['HTTP_REFERER']
    

if Settings.framework == 'flask':
    pass
elif Settings.framework == 'bottle': 
    Framework.run(app=app, host='localhost', port=5000, reloader=True)
else:pass

if Settings.framework == 'flask':
    pass
elif Settings.framework == 'bottle': 
    app = Session.Middleware(app, Session.options)
    @Framework.get('/static/:filename#.+#', name="static")
    def server_static(filename):
        print filename
        return Framework.static_file(filename, root='Site/static/')
else:pass