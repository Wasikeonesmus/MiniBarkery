from django import forms
from .models import Product, Supplier, Recipe, ProductionBatch, Expense

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'supplier', 
                 'stock_quantity', 'minimum_stock_level', 'reorder_quantity', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'price': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'min': '0'}),
            'minimum_stock_level': forms.NumberInput(attrs={'min': '0'}),
            'reorder_quantity': forms.NumberInput(attrs={'min': '0'}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['name', 'description', 'ingredients', 'instructions', 
                 'preparation_time', 'yield_quantity', 'yield_unit']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'ingredients': forms.Textarea(attrs={'rows': 5}),
            'instructions': forms.Textarea(attrs={'rows': 5}),
            'preparation_time': forms.NumberInput(attrs={'min': '0'}),
            'yield_quantity': forms.NumberInput(attrs={'min': '0'}),
            'yield_unit': forms.TextInput(attrs={'placeholder': 'e.g., pieces, kg'}),
        }

class ProductionBatchForm(forms.ModelForm):
    class Meta:
        model = ProductionBatch
        fields = ['recipe', 'batch_number', 'start_time', 'quantity_produced', 'notes']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['date', 'type', 'amount', 'description', 'receipt']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        } 