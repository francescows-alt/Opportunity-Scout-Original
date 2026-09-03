from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tracker", "0008_candidateprofile_linkedin_source")]

    operations = [
        migrations.AddField(model_name="opportunity", name="company_description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="opportunity", name="company_location", field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name="opportunity", name="company_size", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="opportunity", name="internship_dates", field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name="opportunity", name="japanese_requirement", field=models.CharField(blank=True, max_length=240)),
        migrations.AddField(model_name="opportunity", name="requirements_assessment", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="opportunity", name="research_sources", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="opportunity", name="research_summary", field=models.TextField(blank=True)),
        migrations.AddField(model_name="opportunity", name="thesis_compatibility", field=models.CharField(blank=True, max_length=240)),
        migrations.AddField(
            model_name="opportunity",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("pending", "Research needed"), ("qualified", "Qualified"),
                    ("clarify", "Needs clarification"), ("unsuitable", "Unsuitable"),
                    ("unverified", "Could not verify"),
                ],
                db_index=True, default="pending", max_length=20,
            ),
        ),
        migrations.AddField(model_name="opportunity", name="verified_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="opportunity", name="visa_support", field=models.CharField(blank=True, max_length=240)),
        migrations.AddField(model_name="opportunity", name="work_arrangement", field=models.CharField(blank=True, max_length=160)),
    ]
