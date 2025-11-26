import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('medicine', '0001_initial'),
    ]
    operations = [
        migrations.RemoveField(
            model_name='medicine',
            name='expiry_date',
        ),
        migrations.RemoveField(
            model_name='medicine',
            name='stock_quantity',
        ),
        migrations.CreateModel(
            name='MedicineBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_id', models.CharField(db_index=True, max_length=100)),
                ('expiry_date', models.DateField()),
                ('date_received', models.DateField()),
                ('quantity_received', models.IntegerField(default=0)),
                ('quantity_available', models.IntegerField(default=0)),
                ('quantity_dispensed', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='medicine.medicine')),
            ],
            options={
                'db_table': 'tblmedicine_batch',
                'ordering': ['expiry_date', 'batch_id'],
                'managed': True,
                'unique_together': {('batch_id', 'medicine')},
            },
        ),
    ]
