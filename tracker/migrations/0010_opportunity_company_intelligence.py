from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tracker", "0009_opportunity_research_report")]

    operations = [
        migrations.AddField(model_name="opportunity", name="application_deadline_text", field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name="opportunity", name="company_reputation", field=models.TextField(blank=True)),
        migrations.AddField(model_name="opportunity", name="cv_value", field=models.TextField(blank=True)),
        migrations.AddField(model_name="opportunity", name="growth_outlook", field=models.TextField(blank=True)),
        migrations.AddField(model_name="opportunity", name="international_environment", field=models.TextField(blank=True)),
        migrations.AddField(model_name="opportunity", name="responsibilities", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="opportunity", name="work_culture", field=models.TextField(blank=True)),
        migrations.AlterField(
            model_name="opportunity",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("pending", "Research needed"), ("qualified", "Qualified"),
                    ("clarify", "Needs clarification"), ("unsuitable", "Unsuitable"),
                    ("expired", "Expired"), ("unverified", "Could not verify"),
                ],
                db_index=True, default="pending", max_length=20,
            ),
        ),
    ]
