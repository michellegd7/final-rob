from django.urls import path
from . import views

urlpatterns = [
    # Owner
    path('', views.owner, name='owner'),
    path('login/', views.login, name='login'),
    path('owner_register/', views.owner_register, name='owner_register'),
    path('owner_logout/', views.owner_logout, name='owner_logout'),
    path('owner_parking_slots/', views.owner_parking_slots, name='owner_parking_slots'),
    path('owner_reserve_slot/', views.owner_reserve_slot, name='owner_reserve_slot'),
    path('owner_my_ticket/', views.owner_my_ticket, name='owner_my_ticket'),
    path('owner_edit_ticket/<int:ticket_id>/', views.owner_edit_ticket, name='owner_edit_ticket'),
    path('owner_cancel_ticket/<int:ticket_id>/', views.owner_cancel_ticket, name='owner_cancel_ticket'),
    path('owner_vehicle_register/', views.owner_vehicle_register, name='owner_vehicle_register'),
    path('owner_delete_vehicle/<int:vehicle_id>/', views.owner_delete_vehicle, name='owner_delete_vehicle'),

    # Guard
    path('guard_login/', views.guard_login, name='guard_login'),
    path('guard_register/', views.guard_register, name='guard_register'),
    path('guard_logout/', views.guard_logout, name='guard_logout'),
    path('guard_parking_slots/', views.guard_parking_slots, name='guard_parking_slots'),
    path('guard_confirm_slot/', views.guard_confirm_slot, name='guard_confirm_slot'),
    path('guard_checkout/<int:ticket_id>/', views.guard_checkout, name='guard_checkout'),
    path('guard_parking_ticket/', views.guard_parking_ticket, name='guard_parking_ticket'),
    path('guard_cancel_ticket/<int:ticket_id>/', views.guard_cancel_ticket, name='guard_cancel_ticket'),

    # Admin
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin_owners/', views.admin_owners, name='admin_owners'),
    path('admin_guards/', views.admin_guards, name='admin_guards'),
    path('admin_slots/', views.admin_slots, name='admin_slots'),
    path('admin_slots/add/', views.admin_add_slot, name='admin_add_slot'),
    path('admin_tickets/', views.admin_tickets, name='admin_tickets'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),
]