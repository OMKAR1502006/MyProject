from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('agro', '0004_governmentscheme'),
    ]

    operations = [
        migrations.CreateModel(
            name='YieldPredictionHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('crop_type', models.CharField(max_length=80)),
                ('farm_size_acres', models.DecimalField(decimal_places=2, max_digits=8)),
                ('soil_type', models.CharField(max_length=50)),
                ('season', models.CharField(max_length=30)),
                ('rainfall', models.FloatField()),
                ('temperature', models.FloatField()),
                ('seed_cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fertilizer_cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('labor_cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('expected_yield_tonnes', models.FloatField()),
                ('estimated_revenue', models.DecimalField(decimal_places=2, max_digits=12)),
                ('estimated_expenses', models.DecimalField(decimal_places=2, max_digits=12)),
                ('estimated_profit', models.DecimalField(decimal_places=2, max_digits=12)),
                ('profit_margin_percent', models.FloatField()),
                ('recommendations', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='yield_predictions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Yield prediction histories',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='VoiceCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('response_text', models.TextField()),
                ('language', models.CharField(max_length=10)),
                ('generated_audio', models.BinaryField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FavoriteScheme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheme_id', models.CharField(max_length=80)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_schemes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='voicecache',
            index=models.Index(fields=['response_text', 'language'], name='agro_voicec_respons_4bc738_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='favoritescheme',
            unique_together={('user', 'scheme_id')},
        ),
    ]
