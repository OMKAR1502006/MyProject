# Generated migration for GovernmentScheme model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agro', '0003_chathistory'),
    ]

    operations = [
        migrations.CreateModel(
            name='GovernmentScheme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheme_id', models.CharField(max_length=80, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('short_description', models.CharField(blank=True, max_length=500)),
                ('description', models.TextField(blank=True)),
                ('category', models.CharField(default='general', max_length=60)),
                ('states', models.JSONField(blank=True, default=list)),
                ('eligibility', models.TextField(blank=True)),
                ('benefits', models.TextField(blank=True)),
                ('application_steps', models.JSONField(blank=True, default=list)),
                ('apply_url', models.URLField(blank=True, max_length=500)),
                ('last_updated', models.CharField(blank=True, max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['title'],
            },
        ),
    ]
