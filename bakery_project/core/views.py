from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Product, PaymentMethod, Sale, SaleItem, Supplier, Purchase, Expense, FinancialReport, ProductionBatch, Recipe
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta
from django.utils import timezone
import csv
from django.http import HttpResponse
from django.db.models import Sum, Count, F
from .forms import ProductForm, ExpenseForm, RecipeForm, ProductionBatchForm, SupplierForm

def home(request):
    return render(request, 'core/home.html')

def product_list(request):
    products = Product.objects.filter(is_active=True)
    return render(request, 'core/product_list.html', {'products': products})

@login_required
def pos(request):
    products = Product.objects.filter(is_active=True)
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    return render(request, 'core/pos.html', {
        'products': products,
        'payment_methods': payment_methods
    })

@login_required
@csrf_exempt
def process_sale(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_name = data.get('customer_name', 'Walk-in Customer')
            payment_method = data.get('payment_method')
            items = data.get('items', [])

            # Create sale
            sale = Sale.objects.create(
                customer_name=customer_name,
                payment_method=payment_method,
                total_amount=Decimal('0.00')
            )

            total_amount = Decimal('0.00')
            for item in items:
                product = Product.objects.get(id=item['product_id'])
                quantity = int(item['quantity'])
                unit_price = Decimal(str(item['price']))
                total_price = unit_price * quantity

                # Create sale item
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )

                # Update product stock
                product.stock_quantity -= quantity
                product.save()

                total_amount += total_price

            # Update sale total
            sale.total_amount = total_amount
            sale.save()

            return JsonResponse({
                'success': True,
                'sale_id': sale.id,
                'total_amount': str(total_amount)
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@login_required
def dashboard(request):
    # Get today's date
    today = timezone.now().date()
    
    # Get sales data
    today_sales = Sale.objects.filter(sale_date__date=today)
    total_sales = today_sales.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Get low stock products
    low_stock_products = Product.objects.filter(stock_quantity__lte=F('minimum_stock_level'))
    
    # Get recent sales
    recent_sales = Sale.objects.all().order_by('-sale_date')[:5]
    
    context = {
        'total_sales': total_sales,
        'low_stock_products': low_stock_products,
        'recent_sales': recent_sales,
    }
    
    return render(request, 'core/dashboard.html', context)

@login_required
def dashboard_data(request):
    # Get date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=6)
    
    # Get daily sales data
    daily_sales = Sale.objects.filter(
        sale_date__date__range=[start_date, end_date]
    ).values('sale_date__date').annotate(
        total=Sum('total_amount')
    ).order_by('sale_date__date')
    
    # Format data for chart
    dates = [sale['sale_date__date'].strftime('%Y-%m-%d') for sale in daily_sales]
    amounts = [float(sale['total']) for sale in daily_sales]
    
    return JsonResponse({
        'dates': dates,
        'amounts': amounts
    })

@login_required
def purchase_list(request):
    purchases = Purchase.objects.all().order_by('-purchase_date')
    pending_orders = purchases.filter(status='pending')
    ordered_orders = purchases.filter(status='ordered')
    delivered_orders = purchases.filter(status='delivered')
    
    context = {
        'purchases': purchases,
        'pending_orders': pending_orders,
        'ordered_orders': ordered_orders,
        'delivered_orders': delivered_orders,
    }
    return render(request, 'core/purchase_list.html', context)

@login_required
def add_purchase(request):
    if request.method == 'POST':
        # Handle purchase creation
        pass
    return render(request, 'core/add_purchase.html')

@login_required
def supply_receipt(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    return render(request, 'core/supply_receipt.html', {'purchase': purchase})

@login_required
def update_purchase_status(request, purchase_id):
    if request.method == 'POST':
        purchase = get_object_or_404(Purchase, id=purchase_id)
        new_status = request.POST.get('status')
        if new_status in dict(Purchase.STATUS_CHOICES):
            purchase.status = new_status
            purchase.save()
            messages.success(request, 'Purchase status updated successfully!')
    return redirect('purchase_list')

@login_required
def stock_report(request):
    products = Product.objects.all()
    low_stock = [p for p in products if p.needs_restock()]
    return render(request, 'core/stock_report.html', {
        'products': products,
        'low_stock': low_stock
    })

@login_required
def inventory_dashboard(request):
    # Get inventory statistics
    total_products = Product.objects.count()
    low_stock_count = Product.objects.filter(stock_quantity__lte=F('minimum_stock_level')).count()
    out_of_stock = Product.objects.filter(stock_quantity=0).count()
    
    # Get category distribution
    category_distribution = Product.objects.values('category').annotate(
        count=Count('id')
    ).order_by('category')
    
    context = {
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'out_of_stock': out_of_stock,
        'category_distribution': category_distribution,
    }
    return render(request, 'core/inventory_dashboard.html', context)

@login_required
def import_export(request):
    if request.method == 'POST':
        if 'import_file' in request.FILES:
            file = request.FILES['import_file']
            if file.name.endswith('.csv'):
                # Handle CSV import
                reader = csv.DictReader(file.read().decode('utf-8').splitlines())
                for row in reader:
                    if 'product' in request.POST.get('import_type'):
                        Product.objects.create(
                            name=row['name'],
                            description=row['description'],
                            price=row['price'],
                            category=row['category'],
                            stock_quantity=row['stock_quantity'],
                            minimum_stock_level=row['minimum_stock_level'],
                            reorder_quantity=row['reorder_quantity']
                        )
                    elif 'supplier' in request.POST.get('import_type'):
                        Supplier.objects.create(
                            name=row['name'],
                            contact_person=row['contact_person'],
                            phone=row['phone'],
                            email=row['email'],
                            address=row['address']
                        )
                messages.success(request, 'Import completed successfully!')
            else:
                messages.error(request, 'Please upload a CSV file.')
    
    return render(request, 'core/import_export.html', {
        'products': Product.objects.all(),
        'suppliers': Supplier.objects.all()
    })

@login_required
def export_data(request):
    model_type = request.GET.get('type')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{model_type}_export.csv"'
    
    writer = csv.writer(response)
    
    if model_type == 'products':
        writer.writerow(['name', 'description', 'price', 'category', 'stock_quantity', 
                        'minimum_stock_level', 'reorder_quantity'])
        for product in Product.objects.all():
            writer.writerow([
                product.name, product.description, product.price, product.category,
                product.stock_quantity, product.minimum_stock_level, product.reorder_quantity
            ])
    elif model_type == 'suppliers':
        writer.writerow(['name', 'contact_person', 'phone', 'email', 'address'])
        for supplier in Supplier.objects.all():
            writer.writerow([
                supplier.name, supplier.contact_person, supplier.phone,
                supplier.email, supplier.address
            ])
    
    return response

@login_required
def financial_dashboard(request):
    # Get date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get sales and expenses
    sales = Sale.objects.filter(sale_date__date__range=[start_date, end_date])
    expenses = Expense.objects.filter(date__range=[start_date, end_date])
    
    total_sales = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    net_profit = total_sales - total_expenses
    
    # Get expense distribution
    expense_distribution = expenses.values('type').annotate(
        total=Sum('amount')
    ).order_by('type')
    
    context = {
        'total_sales': total_sales,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'expense_distribution': expense_distribution,
    }
    return render(request, 'core/financial_dashboard.html', context)

@login_required
def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense added successfully!')
            return redirect('financial_dashboard')
    else:
        form = ExpenseForm()
    return render(request, 'core/add_expense.html', {'form': form})

@login_required
def production_dashboard(request):
    # Get recent production batches
    recent_batches = ProductionBatch.objects.all().order_by('-start_time')[:5]
    
    # Get active recipes
    active_recipes = Recipe.objects.filter(is_active=True)
    
    context = {
        'recent_batches': recent_batches,
        'active_recipes': active_recipes,
    }
    return render(request, 'core/production_dashboard.html', context)

@login_required
def add_recipe(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Recipe added successfully!')
            return redirect('production_dashboard')
    else:
        form = RecipeForm()
    return render(request, 'core/add_recipe.html', {'form': form})

@login_required
def add_production_batch(request):
    if request.method == 'POST':
        form = ProductionBatchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Production batch added successfully!')
            return redirect('production_dashboard')
    else:
        form = ProductionBatchForm()
    return render(request, 'core/add_production_batch.html', {'form': form})

@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'core/add_product.html', {'form': form})

@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'core/edit_product.html', {'form': form, 'product': product})

@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.is_active = False
        product.save()
        messages.success(request, 'Product deleted successfully!')
        return redirect('product_list')
    return render(request, 'core/delete_product.html', {'product': product})

@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all().order_by('name')
    return render(request, 'core/supplier_list.html', {
        'suppliers': suppliers
    })

@login_required
def add_supplier(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier added successfully!')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'core/add_supplier.html', {'form': form})

@login_required
def edit_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier updated successfully!')
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'core/edit_supplier.html', {'form': form, 'supplier': supplier})

@login_required
def delete_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, 'Supplier deleted successfully!')
        return redirect('supplier_list')
    return render(request, 'core/delete_supplier.html', {'supplier': supplier})
