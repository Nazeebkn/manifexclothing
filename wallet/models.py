from django.db import models
from django.contrib.auth.models import User
from checkout .models import Order
import uuid

# Create your models here.

"""
WALLET INFO
"""
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username}'s wallet"


"""
WALLET TRANSACTIONS TABLE
"""
class WalletTransaction(models.Model):
    TRANSACTION_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=[('credit', 'Credit'), ('debit', 'Debit')])
    status = models.CharField(max_length=10, choices=TRANSACTION_STATUS, default='pending')
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=36, unique=True, default=uuid.uuid4, editable=False)

    def __str__(self):
        return f"{self.transaction_type} of {self.amount} for {self.wallet.user.username}"