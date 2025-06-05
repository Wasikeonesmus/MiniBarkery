from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/data/', views.dashboard_data, name='dashboard_data'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('pos/', views.pos, name='pos'),
    path('pos/process-sale/', views.process_sale, name='process_sale'),
    path('purchases/', views.purchase_list, name='purchase_list'),
    path('purchases/add/', views.add_purchase, name='add_purchase'),
    path('purchases/<int:purchase_id>/receipt/', views.supply_receipt, name='supply_receipt'),
    path('purchases/<int:purchase_id>/update-status/', views.update_purchase_status, name='update_purchase_status'),
    path('stock-report/', views.stock_report, name='stock_report'),
    path('inventory-dashboard/', views.inventory_dashboard, name='inventory_dashboard'),
    path('import-export/', views.import_export, name='import_export'),
    path('export-data/', views.export_data, name='export_data'),
    
    # Supplier Management URLs
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('suppliers/<int:supplier_id>/edit/', views.edit_supplier, name='edit_supplier'),
    path('suppliers/<int:supplier_id>/delete/', views.delete_supplier, name='delete_supplier'),
    
    # Financial Management URLs
    path('financial/', views.financial_dashboard, name='financial_dashboard'),
    path('financial/expense/add/', views.add_expense, name='add_expense'),
    
    # Production Management URLs
    path('production/', views.production_dashboard, name='production_dashboard'),
    path('production/recipe/add/', views.add_recipe, name='add_recipe'),
    path('production/batch/add/', views.add_production_batch, name='add_production_batch'),
] 