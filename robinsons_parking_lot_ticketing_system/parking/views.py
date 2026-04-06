from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import Slot, Ticket, Guard, Vehicle, Owner, Payment
from django.contrib import messages
import json


VEHICLE_RATES = {
    'Car': 100,
    'Motorcycle': 50,
    'Van': 150,
}


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', 'owner')

        if role == 'owner':
            try:
                owner = Owner.objects.get(username=username, password=password)
                request.session['owner_id'] = owner.id
                return redirect('/')
            except Owner.DoesNotExist:
                return render(request, 'login.html', {
                    'error': 'Invalid owner username or password.'
                })

        elif role == 'guard':
            try:
                guard = Guard.objects.get(username=username, password=password)
                request.session['guard_id'] = guard.id
                return redirect('guard_parking_slots')
            except Guard.DoesNotExist:
                return render(request, 'login.html', {
                    'error': 'Invalid guard username or password.'
                })

        elif role == 'admin':
            if username == 'admin' and password == 'admin123':
                request.session['is_admin'] = True
                return redirect('admin_dashboard')
            else:
                return render(request, 'login.html', {
                    'error': 'Invalid admin username or password.'
                })

    return render(request, 'login.html')


def owner(request):
    owner = None
    if request.session.get('owner_id'):
        owner = Owner.objects.filter(id=request.session['owner_id']).first()
    return render(request, 'owner.html', {'owner': owner})


def owner_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')

        if Owner.objects.filter(username=username).exists():
            return render(request, 'owner_register.html', {
                'error': 'Username already taken. Please choose another.'
            })

        Owner.objects.create(
            first_name=first_name,
            last_name=last_name,
            username=username,
            password=password,
            phone_number=phone_number,
            address=address,
        )
        return redirect('login')

    return render(request, 'owner_register.html')

def owner_parking_slots(request):
    if not request.session.get('owner_id'):
        return redirect('login')

    owner = Owner.objects.filter(id=request.session['owner_id']).first()
    slots = list(Slot.objects.all())

    active_tickets = Ticket.objects.filter(
        status='active'
    ).select_related('vehicle', 'slot').prefetch_related('payment_set')

    ticket_map = {t.slot_id: t for t in active_tickets}

    for slot in slots:
        ticket = ticket_map.get(slot.id)
        slot.active_ticket = ticket

        if ticket:
            vtype = ticket.vehicle.vehicle_type
            ticket.computed_fee = VEHICLE_RATES.get(vtype, 100)
            pay = ticket.payment_set.last()
            ticket.payment_method = pay.payment_method if pay else 'pay_on_arrival'
            ticket.payment_ref    = 'N/A'
            ticket.payment_status = 'paid' if pay else 'pending'

    return render(request, 'owner_parking_slots.html', {
        'owner': owner,
        'slots': slots,
    })

def owner_vehicle_register(request):
    if not request.session.get('owner_id'):
        return redirect('login')

    owner    = Owner.objects.get(id=request.session['owner_id'])
    vehicles = Vehicle.objects.filter(owner=owner).order_by('plate_number')

    if request.method == 'POST':
        plate_number  = request.POST.get('plate_number', '').strip().upper()
        vehicle_type  = request.POST.get('vehicle_type', '').strip()

        if not plate_number or not vehicle_type:
            return render(request, 'owner_vehicle_register.html', {
                'owner':     owner,
                'vehicles':  vehicles,
                'error':     'Plate number and vehicle type are required.',
                'form_data': request.POST,
            })

        if Vehicle.objects.filter(plate_number=plate_number).exists():
            return render(request, 'owner_vehicle_register.html', {
                'owner':     owner,
                'vehicles':  vehicles,
                'error':     f'Plate number "{plate_number}" is already registered.',
                'form_data': request.POST,
            })

        Vehicle.objects.create(
            owner        = owner,
            plate_number = plate_number,
            vehicle_type = vehicle_type,
        )

        vehicles = Vehicle.objects.filter(owner=owner).order_by('plate_number')
        return render(request, 'owner_vehicle_register.html', {
            'owner':    owner,
            'vehicles': vehicles,
            'success':  f'{plate_number} has been registered successfully.',
        })

    return render(request, 'owner_vehicle_register.html', {
        'owner':    owner,
        'vehicles': vehicles,
    })


def owner_delete_vehicle(request, vehicle_id):
    if not request.session.get('owner_id'):
        return redirect('login')

    if request.method == 'POST':
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id, owner__id=request.session['owner_id'])
            vehicle.delete()
        except Vehicle.DoesNotExist:
            pass

    return redirect('owner_vehicle_register')


def owner_reserve_slot(request):
    """Owner reserves a slot — standard form POST."""
    if not request.session.get('owner_id'):
        return redirect('login')

    if request.method == 'POST':
        slot_id = request.POST.get('slot_id')
        plate_number = request.POST.get('plate_number', '').strip()
        vehicle_type = request.POST.get('vehicle_type', 'Car')
        start_time = request.POST.get('start_time', '')
        end_time = request.POST.get('end_time', '')
        payment_method = request.POST.get('payment_method', 'pay_on_arrival')
        payment_ref = request.POST.get('payment_ref', '').strip()

        if not slot_id or not plate_number:
            slots = Slot.objects.all()
            owner = Owner.objects.filter(id=request.session['owner_id']).first()
            return render(request, 'owner_parking_slots.html', {
                'slots': slots, 'owner': owner,
                'error': 'Plate number is required.',
            })

        try:
            slot = Slot.objects.get(id=slot_id, slot_status='available')
        except Slot.DoesNotExist:
            slots = Slot.objects.all()
            owner = Owner.objects.filter(id=request.session['owner_id']).first()
            return render(request, 'owner_parking_slots.html', {
                'slots': slots, 'owner': owner,
                'error': 'This slot is no longer available.',
            })

        owner = Owner.objects.get(id=request.session['owner_id'])
        vehicle, _ = Vehicle.objects.get_or_create(
            plate_number=plate_number,
            defaults={'vehicle_type': vehicle_type, 'owner': owner}
        )

        parsed_entry = parse_datetime(start_time) if start_time else timezone.now()
        parsed_exit  = parse_datetime(end_time)   if end_time   else None

        ticket = Ticket.objects.create(
            vehicle=vehicle,
            slot=slot,
            owner=owner,
            status='active',
            entry_time=parsed_entry,
            exit_time=parsed_exit,
        )

        Payment.objects.create(
            ticket=ticket,
            amount=VEHICLE_RATES.get(vehicle_type, 100),
            payment_method=payment_method,         
            payment_ref=payment_ref,             
        )

        slot.slot_status = 'occupied'
        slot.save()

        return redirect('owner_my_ticket')

    return redirect('owner_parking_slots')


def owner_my_ticket(request):
    if not request.session.get('owner_id'):
        return redirect('login')

    owner = Owner.objects.get(id=request.session['owner_id'])

    tickets = Ticket.objects.filter(
        vehicle__owner=owner
    ).select_related('vehicle', 'slot').order_by('-id')  

    return render(request, 'owner_my_ticket.html', {
        'owner':   owner,
        'tickets': tickets,
    })  
 
def owner_cancel_ticket(request, ticket_id):
    if not request.session.get('owner_id'):
        return redirect('login')
 
    if request.method == 'POST':
        try:
            ticket = Ticket.objects.get(id=ticket_id, status='active')
            ticket.status = 'cancelled'
            ticket.save()
            ticket.slot.slot_status = 'available'
            ticket.slot.save()
            return redirect('owner_my_ticket')
        except Ticket.DoesNotExist:
            pass
 
    return redirect('owner_my_ticket')
 
 
def owner_edit_ticket(request, ticket_id):
    if not request.session.get('owner_id'):
        return redirect('login')
 
    if request.method == 'POST':
        from django.utils.dateparse import parse_datetime
        plate_number = request.POST.get('plate_number', '').strip()
        vehicle_type = request.POST.get('vehicle_type', 'Car')
        entry_time   = request.POST.get('entry_time', '')
        exit_time    = request.POST.get('exit_time', '')
 
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            ticket.vehicle.plate_number  = plate_number
            ticket.vehicle.vehicle_type  = vehicle_type
            ticket.vehicle.save()
            if entry_time:
                ticket.entry_time = parse_datetime(entry_time)
            if exit_time:
                ticket.exit_time = parse_datetime(exit_time)
            else:
                ticket.exit_time = None
            ticket.save()
        except Ticket.DoesNotExist:
            pass
 
    return redirect('owner_my_ticket')

def owner_logout(request):
    request.session.flush()
    return redirect('owner')


def guard_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            guard = Guard.objects.get(username=username, password=password)
            request.session['guard_id'] = guard.id
            return redirect('guard_parking_slots')
        except Guard.DoesNotExist:
            return render(request, 'login.html', {'error': 'Invalid username or password.'})
    return render(request, 'login.html')


def guard_register(request):
    if request.method == 'POST':
        username     = request.POST.get('username')
        password     = request.POST.get('password')
        first_name   = request.POST.get('first_name')
        last_name    = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        address      = request.POST.get('address', '')

        if Guard.objects.filter(username=username).exists():
            return render(request, 'guard_register.html', {
                'error': 'Username already taken. Please choose another.'
            })

        Guard.objects.create(
            first_name=first_name,
            last_name=last_name,
            username=username,
            password=password,
            phone_number=phone_number,
            address=address,
        )
        return redirect('login')

    return render(request, 'guard_register.html')


def guard_logout(request):
    request.session.flush()
    return redirect('login')


def guard_parking_slots(request):
    if 'guard_id' not in request.session:
        return redirect('login')

    guard  = Guard.objects.get(id=request.session['guard_id'])
    slots  = list(Slot.objects.all())
    owners = Owner.objects.all().order_by('first_name', 'last_name')

    active_tickets = Ticket.objects.filter(
        status='active'
    ).select_related('vehicle', 'slot')

    ticket_map = {t.slot_id: t for t in active_tickets}
    for slot in slots:
        slot.active_ticket = ticket_map.get(slot.id)

    return render(request, 'guard_parking_slots.html', {
        'guard':  guard,
        'slots':  slots,
        'owners': owners,
    })


def guard_confirm_slot(request):
    """AJAX: Guard marks a slot as occupied and creates a ticket + payment record."""
    if 'guard_id' not in request.session:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    try:
        data         = json.loads(request.body)
        slot_id      = data.get('slot_id')
        owner_id     = data.get('owner_id')
        plate_number = data.get('plate_number', '').strip()
        vehicle_type = data.get('vehicle_type', 'Car')
        start_time   = data.get('start_time')
        end_time     = data.get('end_time')

        if not owner_id:
            return JsonResponse({'success': False, 'error': 'Please select an owner.'})
        if not plate_number:
            return JsonResponse({'success': False, 'error': 'Plate number is required.'})

        try:
            slot = Slot.objects.get(id=slot_id, slot_status='available')
        except Slot.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Slot no longer available.'})

        try:
            owner = Owner.objects.get(id=owner_id)
        except Owner.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Owner not found.'})

        vehicle, _ = Vehicle.objects.get_or_create(
            plate_number=plate_number,
            defaults={'vehicle_type': vehicle_type, 'owner': owner}
        )
        if vehicle.vehicle_type != vehicle_type:
            vehicle.vehicle_type = vehicle_type
            vehicle.save()

        guard = Guard.objects.get(id=request.session['guard_id'])

        entry = parse_datetime(start_time) if start_time else timezone.now()
        exit_ = parse_datetime(end_time)   if end_time   else None

        ticket = Ticket.objects.create(
            vehicle=vehicle,
            guard=guard,
            slot=slot,
            owner=owner,
            status='active',
            entry_time=entry,
            exit_time=exit_,
        )

        Payment.objects.create(
            ticket=ticket,
            amount=VEHICLE_RATES.get(vehicle_type, 100),
            payment_method='pay_on_arrival',
        )

        slot.slot_status = 'occupied'
        slot.save()

        return JsonResponse({'success': True, 'ticket_id': ticket.id})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def guard_checkout(request, ticket_id):
    """Guard checks out a vehicle — standard form POST."""
    if 'guard_id' not in request.session:
        return redirect('login')

    if request.method == 'POST':
        try:
            ticket    = Ticket.objects.select_related('slot').get(
                id=ticket_id, status='active'
            )
            exit_str  = request.POST.get('exit_time', '').strip()
            exit_time = parse_datetime(exit_str) if exit_str else timezone.now()
            if not exit_time:
                exit_time = timezone.now()

            ticket.exit_time = exit_time
            ticket.status    = 'completed'
            ticket.guard_id  = request.session['guard_id']  # ← assign the guard
            ticket.save()

            ticket.slot.slot_status = 'available'
            ticket.slot.save()

        except Ticket.DoesNotExist:
            pass

    return redirect('guard_parking_ticket')


def guard_cancel_ticket(request, ticket_id):
    """Guard cancels a ticket — standard form POST."""
    if 'guard_id' not in request.session:
        return redirect('login')

    if request.method == 'POST':
        try:
            ticket = Ticket.objects.get(id=ticket_id, status='active')
            ticket.status = 'cancelled'
            ticket.save()
            ticket.slot.slot_status = 'available'
            ticket.slot.save()
        except Ticket.DoesNotExist:
            pass

    return redirect('guard_parking_ticket')


def guard_parking_ticket(request):
    if 'guard_id' not in request.session:
        return redirect('login')
    guard = Guard.objects.get(id=request.session['guard_id'])
    tickets = Ticket.objects.select_related(
        'vehicle', 'slot', 'guard'
    ).prefetch_related('payment_set').order_by('-entry_time')
    return render(request, 'guard_parking_ticket.html', {
        'guard':   guard,
        'tickets': tickets,
    })
    
 
def _admin_required(request):
    return request.session.get('is_admin', False)
 
 
def admin_dashboard(request):
    if not _admin_required(request):
        return redirect('login')
 
    RATES = { 'Car': 100, 'Motorcycle': 50, 'Van': 150 }
 
    completed_tickets = Ticket.objects.filter(
        status='completed'
    ).select_related('vehicle')
 
    total_sales = sum(
        RATES.get(t.vehicle.vehicle_type, 100)
        for t in completed_tickets
    )
 
    context = {
        'total_slots':       Slot.objects.count(),
        'available_slots':   Slot.objects.filter(slot_status='available').count(),
        'occupied_slots':    Slot.objects.filter(slot_status='occupied').count(),
        'total_tickets':     Ticket.objects.count(),
        'active_tickets':    Ticket.objects.filter(status='active').count(),
        'cancelled_tickets': Ticket.objects.filter(status='cancelled').count(),
        'total_owners':      Owner.objects.count(),
        'total_guards':      Guard.objects.count(),
        'recent_tickets':    Ticket.objects.select_related('vehicle', 'slot').order_by('-id')[:10],
        'total_sales':       total_sales,
        'guards':            Guard.objects.all().order_by('first_name'),
        'owners':            Owner.objects.all().order_by('first_name'),
    }
    return render(request, 'admin_dashboard.html', context)
 
 
def admin_owners(request):
    if not _admin_required(request):
        return redirect('login')
    
    owners = Owner.objects.all().order_by('id')
    active_owners = Owner.objects.filter(
        tickets__status='active'
    ).distinct().count()

    all_vehicles = Vehicle.objects.select_related('owner').all()
    vehicles_by_owner = {}
    for v in all_vehicles:
        vehicles_by_owner.setdefault(v.owner_id, []).append({
            'type':  v.vehicle_type,
            'plate': v.plate_number,
        })

    for o in owners:
        o.vehicles_data = vehicles_by_owner.get(o.id, [])

    return render(request, 'admin_owners.html', {
        'owners':        owners,
        'active_owners': active_owners,
    })
 
def admin_guards(request):
    if not _admin_required(request):
        return redirect('login')
    guards = Guard.objects.all().order_by('id')
    active_guards = Guard.objects.filter(
        ticket__status='active'
    ).distinct().count()
    return render(request, 'admin_guards.html', {
        'guards': guards,
        'active_guards': active_guards,
    })
 
 
def admin_slots(request):
    if not _admin_required(request):
        return redirect('login')
    slots = list(Slot.objects.all())
    active_tickets = Ticket.objects.filter(
        status='active'
    ).select_related('vehicle', 'slot')
    ticket_map = {t.slot_id: t for t in active_tickets}
    for slot in slots:
        slot.active_ticket = ticket_map.get(slot.id)
    return render(request, 'admin_slots.html', {'slots': slots})

def admin_add_slot(request):
    if request.method == 'POST':
        slot_number = request.POST.get('slot_number', '').strip()
        slot_type   = request.POST.get('slot_type', '').strip()

        if slot_number and slot_type:
            if Slot.objects.filter(slot_number=slot_number).exists():  # use your actual model name
                messages.error(request, f'Slot "{slot_number}" already exists.')
            else:
                Slot.objects.create(  # use your actual model name
                    slot_number=slot_number,
                    slot_type=slot_type,
                    slot_status='available'
                )
                messages.success(request, f'Slot {slot_number} added successfully.')
        else:
            messages.error(request, 'Please fill in all fields.')

    return redirect('admin_slots')

def admin_tickets(request):
    if not _admin_required(request):
        return redirect('login')
    tickets = Ticket.objects.select_related(
        'vehicle', 'slot', 'guard'
    ).order_by('-entry_time')
    return render(request, 'admin_tickets.html', {'tickets': tickets})
 
 
def admin_logout(request):
    request.session.flush()
    return redirect('login')