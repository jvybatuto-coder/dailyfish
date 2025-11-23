from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Product, CartItem

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'address', 'id_verification', 'password1', 'password2']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price_per_kilo', 'stock_quantity', 'image', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'price_per_kilo': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

class CartForm(forms.Form):
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity_kg = forms.DecimalField(
        max_digits=8, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'class': 'form-control'}),
        label='Quantity (kg)'
    )
