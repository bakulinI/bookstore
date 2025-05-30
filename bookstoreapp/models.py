from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal

class User(AbstractUser):
    username = models.CharField(verbose_name='Имя пользователя', max_length=150, null=False, unique=True)
    email = models.EmailField(unique=True, null=True, default=None, blank=True)
    role = models.CharField(max_length=10,verbose_name= 'Роль', choices=[('reader', 'Reader'), ('admin', 'Admin')],default='reader')

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    genre = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=[('pending', 'Pending'), ('done', 'Done')],
        default='pending'
    )

    def __str__(self):
        return f"Order {self.id} - {self.user.username if self.user else 'Anonymous'}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}x {self.book.title}"

class BookStats(models.Model):
    book = models.OneToOneField(Book, on_delete=models.CASCADE)
    views = models.PositiveIntegerField(default=0)
    rating_sum = models.PositiveIntegerField(default=0)
    rating_count = models.PositiveIntegerField(default=0)

    @property
    def average_rating(self):
        if self.rating_count == 0:
            return 0
        return self.rating_sum / self.rating_count

    def __str__(self):
        return f"Stats for {self.book.title}"

class BookCover(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='bookcover_set')
    image_path = models.CharField(max_length=255, help_text='Путь к изображению в папке static/images', null=True, blank=True)

    def __str__(self):
        return f"Обложка для {self.book.title}"

    class Meta:
        ordering = ['-id']
