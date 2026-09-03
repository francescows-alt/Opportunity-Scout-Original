from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0014_searchcycle_fee_blocked_count_searchjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunity",
            name="internship_start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="internship_end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="minimum_duration",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="posting_language",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="posting_language_note",
            field=models.CharField(blank=True, max_length=300),
        ),
    ]
