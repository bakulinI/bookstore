from django.urls import path
from . import views
from django.views.decorators.http import require_POST

urlpatterns = [
    path('', views.home, name='home'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/export-stats/', views.export_book_stats, name='export_book_stats'),
    path('register/', views.register, name='register'),
    path('catalog/', views.catalog_view, name='catalog'),
    path('cart/add/<int:book_id>/', require_POST(views.add_to_cart), name='add_to_cart'),
    
    # Админ-панель книг
    path('admin/books/', views.admin_book_list, name='admin_book_list'),
    path('admin/books/add/', views.add_book, name='add_book'),
    path('admin/books/<int:book_id>/edit/', views.edit_book, name='edit_book'),
    path('admin/books/<int:book_id>/delete/', views.delete_book, name='delete_book'),

    # Оценка книги
    path('book/<int:book_id>/rate/', require_POST(views.rate_book), name='rate_book'),
]