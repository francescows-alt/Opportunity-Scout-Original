from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tracker", "0007_candidateprofile_document_structured_proposal_and_more")]

    operations = [
        migrations.AddField(
            model_name="candidateprofile",
            name="linkedin_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="candidateprofile",
            name="linkedin_source_text",
            field=models.TextField(
                blank=True,
                help_text="Text copied from LinkedIn. Kept as private evidence for profile comparison.",
            ),
        ),
    ]
