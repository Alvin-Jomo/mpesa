# Generated by Django 5.2.3 on 2025-07-02 08:42

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MpesaPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('checkout_request_id', models.CharField(max_length=50, unique=True)),
                ('phone_number', models.CharField(max_length=15)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('reference', models.CharField(max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=15)),
                ('merchant_request_id', models.CharField(blank=True, max_length=50, null=True)),
                ('mpesa_receipt_number', models.CharField(blank=True, max_length=50, null=True)),
                ('result_code', models.IntegerField(blank=True, null=True)),
                ('result_description', models.TextField(blank=True, null=True)),
                ('callback_metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('callback_received_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'M-Pesa Payment',
                'verbose_name_plural': 'M-Pesa Payments',
                'ordering': ['-created_at'],
            },
        ),
    ]
