from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore

def make_session_cookie_for_user(user, domain):
    s = SessionStore()
    s['_auth_user_id'] = str(user.pk)
    s['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
    s['_auth_user_hash'] = user.get_session_auth_hash()
    s.save()
    cookie = {
        'name': settings.SESSION_COOKIE_NAME,
        'value': s.session_key,
        'domain': domain,
        'path': '/',
        'httpOnly': True,
        'secure': settings.SESSION_COOKIE_SECURE,
        'sameSite': 'Lax',
    }
    return s, cookie
