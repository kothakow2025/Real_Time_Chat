# Generated by Django 4.2.7 on 2025-07-04 12:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_userprofile_bio_userprofile_show_online_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='profile_picture',
            field=models.ImageField(blank=True, default='profile_pics/default.svg', upload_to='profile_pics/'),
        ),
    ]
