from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from .models import User

def get_user_from_token(token):
    try:
        access = AccessToken(token)
        user_id = access['user_id']
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        access_token = None

        #обновление access по refresh токену
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT['REFRESH_TOKEN_COOKIE_NAME'])
        if refresh_token:
            try:
                refresh = RefreshToken(refresh_token)
                access_token = str(refresh.access_token)
            except Exception:
                pass

        if access_token:
            request.user = get_user_from_token(access_token)
        else:
            request.user = AnonymousUser()

        return self.get_response(request)