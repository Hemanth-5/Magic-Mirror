from flask_app import app

# Vercel calls this function
def handler(request, response):
    return app.wsgi_app(request.environ, response)
