from django.db import migrations, models


def label_existing_japanese_only(apps, schema_editor):
    Opportunity = apps.get_model("tracker", "Opportunity")
    Opportunity.objects.filter(
        posting_language__iexact="Japanese",
        japanese_requirement__iexact="Not stated",
    ).update(
        japanese_only_inferred=True,
        japanese_requirement="Japanese-only (inferred)",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0015_opportunity_language_and_dates"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunity",
            name="japanese_only_inferred",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(label_existing_japanese_only, migrations.RunPython.noop),
    ]
