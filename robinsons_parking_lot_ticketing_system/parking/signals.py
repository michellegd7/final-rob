from paypal.standard.models import ST_PP_COMPLETED
from paypal.standard.ipn.signals import valid_ipn_received

def payment_received(sender, **kwargs):
    ipn_obj = sender
    if ipn_obj.payment_status == ST_PP_COMPLETED:
        # Mark the ticket as paid
        ticket = Ticket.objects.get(id=ipn_obj.invoice)
        ticket.is_paid = True
        ticket.save()

valid_ipn_received.connect(payment_received)