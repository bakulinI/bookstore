from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Book, Order, OrderItem, BookCover
import os
from django.conf import settings

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class BookForm(forms.ModelForm):
    image = forms.FileField(required=False, label='Обложка книги', widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Book
        fields = ['title', 'author', 'description', 'price', 'genre']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'price': forms.NumberInput(attrs={'min': 0}),
        }

    def save(self, commit=True):
        book = super().save(commit=commit)
        if self.cleaned_data.get('image'):
            image = self.cleaned_data['image']
            filename = f"images/{book.id}_{image.name}"

            static_dir = os.path.join(settings.STATICFILES_DIRS[0], 'images')
            os.makedirs(static_dir, exist_ok=True)
            
            with open(os.path.join(static_dir, f"{book.id}_{image.name}"), 'wb+') as destination:
                for chunk in image.chunks():
                    destination.write(chunk)

            BookCover.objects.create(
                book=book,
                image_path=filename
            )
        return book

class BookCoverForm(forms.ModelForm):
    class Meta:
        model = BookCover
        fields = ['image_path']
        widgets = {
            'image_path': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #список всех изображений из папки static/images
        images_dir = os.path.join(settings.STATICFILES_DIRS[0], 'images')
        image_files = []
        
        if os.path.exists(images_dir):
            for file in os.listdir(images_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    image_files.append((f'images/{file}', file))
        
        self.fields['image_path'].choices = [('', 'Выберите изображение')] + image_files

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['book', 'quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1})
        }

class BookSearchForm(forms.Form):
    query = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Search books...'}))
    genre = forms.CharField(required=False)
    min_price = forms.DecimalField(required=False, decimal_places=2)
    max_price = forms.DecimalField(required=False, decimal_places=2)