from django.db import migrations, models


def add_logo_if_not_exists(apps, schema_editor):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='organizations_organization' AND column_name='logo';")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE organizations_organization ADD COLUMN logo varchar(100) NULL;")


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0007_alter_organization_theme'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_logo_if_not_exists, reverse_code=migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='organization',
                    name='logo',
                    field=models.ImageField(blank=True, null=True, upload_to='org_logos/'),
                ),
            ],
        ),
    ]
