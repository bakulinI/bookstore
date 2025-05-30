import csv
from datetime import datetime
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from .models import Book, Order, OrderItem, BookStats, BookCover, User
from .forms import (
    UserRegistrationForm, BookSearchForm, BookForm
)
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

# Utils
def is_admin(user):
    try:
        return user.is_authenticated and user.role == 'admin'
    except (AttributeError, TypeError):
        return False

def set_jwt_cookie(response, user):
    refresh = RefreshToken.for_user(user)
    response.set_cookie(
        key=settings.SIMPLE_JWT['REFRESH_TOKEN_COOKIE_NAME'],
        value=str(refresh),
        httponly=True,
        secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
        samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
        max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
        expires=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
    )
    return refresh


# Views

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            response = redirect('home')
            set_jwt_cookie(response, user)
            messages.success(request, f"Добро пожаловать, {user.username}!")
            return response
    else:
        form = UserRegistrationForm()
    return render(request, 'bookstore/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            response = redirect('home')
            refresh = set_jwt_cookie(response, user)
            messages.success(request, f"Добро пожаловать, {user.username}!")
            return response
        else:
            messages.error(request, "Неверные данные для входа")
    return render(request, 'bookstore/login.html')


def logout_view(request):
    logout(request)  # Выполняем выход пользователя
    response = redirect('home')
    response.delete_cookie(settings.SIMPLE_JWT['REFRESH_TOKEN_COOKIE_NAME'])
    messages.success(request, "Вы вышли из аккаунта")
    return response


def home(request):
    # Получаем первые 10 книг из базы данных
    all_books = Book.objects.all()[:10]

    # Разделяем книги на две подборки
    recommended_books = all_books[:5]
    new_books = all_books[5:10]

    search_form = BookSearchForm(request.GET)

    # Логика фильтрации

    return render(request, 'bookstore/home.html', {
        'recommended_books': recommended_books,
        'new_books': new_books,
        'search_form': search_form
    })


def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    stats, created = BookStats.objects.get_or_create(book=book)
    stats.views += 1
    stats.save()

    return render(request, 'bookstore/book_detail.html', {
        'book': book,
        'stats': stats
    })


def login_required_view(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user or isinstance(request.user, AnonymousUser) or not request.user.is_authenticated:
            messages.error(request, 'Требуется авторизация')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required_view
def cart(request):
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        action = request.POST.get('action')
        book = get_object_or_404(Book, id=book_id)
        cart = request.session.get('cart', {})

        book_id_str = str(book_id)
        
        if action == 'increase':
            cart[book_id_str] = cart.get(book_id_str, 0) + 1
        elif action == 'decrease':
            if cart.get(book_id_str, 0) > 1:
                cart[book_id_str] -= 1
            else:
                del cart[book_id_str]
        elif action == 'remove':
            if book_id_str in cart:
                del cart[book_id_str]
        
        request.session['cart'] = cart
        messages.success(request, 'Корзина обновлена')
        return redirect('cart')

    cart = request.session.get('cart', {})
    cart_items = []
    total = 0

    for book_id, quantity in cart.items():
        book = get_object_or_404(Book, id=int(book_id))
        subtotal = book.price * quantity
        cart_items.append({
            'book': book,
            'quantity': quantity,
            'subtotal': subtotal
        })
        total += subtotal

    return render(request, 'bookstore/cart.html', {
        'cart_items': cart_items,
        'total': total
    })


@login_required_view
def checkout(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        if not cart:
            return JsonResponse({
                'success': False,
                'error': 'Корзина пуста'
            })

        try:
            # Создаем заказ
            order = Order.objects.create(
                user=request.user,
                status='pending'  # Статус по умолчанию
            )

            # Добавляем товары в заказ
            for book_id, quantity in cart.items():
                book = get_object_or_404(Book, id=book_id)
                OrderItem.objects.create(
                    order=order,
                    book=book,
                    quantity=quantity
                )

            # Очищаем корзину
            request.session['cart'] = {}
            
            return JsonResponse({
                'success': True,
                'redirect_url': '/cart/'  # Перенаправляем на корзину
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    return JsonResponse({
        'success': False,
        'error': 'Неверный метод запроса'
    })

@login_required_view
def admin_dashboard(request):
    if not is_admin(request.user):
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')
        
    books = Book.objects.all()
    orders = Order.objects.all().order_by('-created_at') # все заказы по дате создания
    total_orders = orders.count() # общее количество
    total_users = User.objects.count()

    return render(request, 'bookstore/admin/dashboard.html', {
        'books': books,
        'orders': orders,
        'total_orders': total_orders,
        'total_users': total_users
    })


@user_passes_test(is_admin)
def export_book_stats(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="book_stats_{datetime.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Название книги ', 'Просмотры ', 'Средняя оценка ', 'Кол-во заказов '])

    for book in Book.objects.all():
        stats = BookStats.objects.get(book=book)
        order_count = OrderItem.objects.filter(book=book).count()
        writer.writerow([
            book.title,
            stats.views,
            stats.average_rating,
            order_count
        ])

    return response

def catalog_view(request):
    books = Book.objects.all()
    
    # параметры фильтрации и сортировки
    query = request.GET.get('query')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    sort = request.GET.get('sort')
    
    
    # поиск по названию
    if query:
        books = books.filter(title__icontains=query)
    
    # фильтры по цене
    if price_min:
        books = books.filter(price__gte=price_min)
    if price_max:
        books = books.filter(price__lte=price_max)
    
    # сортировка
    if sort:
        if sort == 'price_asc':
            books = books.order_by('price')
        elif sort == 'price_desc':
            books = books.order_by('-price')
        elif sort == 'title_asc':
            books = books.order_by('title')
        elif sort == 'title_desc':
            books = books.order_by('-title')
        elif sort == 'author_asc':
            books = books.order_by('author')
        elif sort == 'author_desc':
            books = books.order_by('-author')
    
    # Пагинация
    paginator = Paginator(books, 12)  # 12 книг на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'books': page_obj,
        'current_query': query,
        'current_price_min': price_min,
        'current_price_max': price_max,
        'current_sort': sort,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    return render(request, 'bookstore/catalog.html', context)

@login_required_view
def add_book(request):
    if not is_admin(request.user):
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')
        
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f'Книга "{book.title}" успешно добавлена')
            return redirect('book_detail', book_id=book.id)
    else:
        form = BookForm()
    
    return render(request, 'bookstore/admin/add_book.html', {'form': form})

@login_required_view
def admin_book_list(request):
    if not is_admin(request.user):
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')
        
    books = Book.objects.all()
    
    # параметры фильтрации и сортировки
    search = request.GET.get('search')
    sort = request.GET.get('sort')
    
    # поиск
    if search:
        books = books.filter(
            Q(title__icontains=search) |
            Q(author__icontains=search)
        )
    
    # сортировка
    if sort:
        if sort == 'price_asc':
            books = books.order_by('price')
        elif sort == 'price_desc':
            books = books.order_by('-price')
        elif sort == 'title_asc':
            books = books.order_by('title')
        elif sort == 'title_desc':
            books = books.order_by('-title')
    
    # Пагинация
    paginator = Paginator(books, 10)  # 10 книг на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'books': page_obj,
        'current_search': search,
        'current_sort': sort,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    return render(request, 'bookstore/admin/book_list.html', context)

@login_required_view
def edit_book(request, book_id):
    if not is_admin(request.user):
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')
        
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f'Книга "{book.title}" успешно обновлена')
            return redirect('admin_book_list')
    else:
        form = BookForm(instance=book)
    
    return render(request, 'bookstore/admin/edit_book.html', {
        'form': form,
        'book': book
    })

@login_required_view
def delete_book(request, book_id):
    if not is_admin(request.user):
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('home')
        
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'Книга "{title}" успешно удалена')
        return redirect('admin_book_list')
    
    return redirect('admin_book_list')

@login_required_view
def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    cart = request.session.get('cart', {})
    
    # Преобразуем book_id в строку для использования в качестве ключа
    book_id_str = str(book_id)
    
    # Добавляем книгу в корзину или увеличиваем количество
    cart[book_id_str] = cart.get(book_id_str, 0) + 1
    request.session['cart'] = cart
    
    messages.success(request, f'Книга "{book.title}" добавлена в корзину')

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    else:
        return redirect('home')

@login_required_view
@require_POST
def rate_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    rating = request.POST.get('rating')
    
    if rating:
        try:
            rating = int(rating) # Преобразуем оценку в целое число
            if 1 <= rating <= 5: # Проверяем, что оценка в допустимом диапазоне
                stats, created = BookStats.objects.get_or_create(book=book)
                stats.rating_sum += rating
                stats.rating_count += 1
                stats.save()
                messages.success(request, 'Ваша оценка принята!')
            else:
                messages.error(request, 'Недопустимое значение оценки.')
        except (ValueError, TypeError):
            messages.error(request, 'Неверный формат оценки.')
    else:
        messages.error(request, 'Оценка не была предоставлена.')

    # Перенаправляем пользователя обратно на страницу книги
    return redirect('book_detail', book_id=book.id)