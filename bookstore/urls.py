from django.contrib import admin
from django.urls import path, include
from bookstoreapp import views
urlpatterns = [
    path('', include('bookstoreapp.urls')),
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
