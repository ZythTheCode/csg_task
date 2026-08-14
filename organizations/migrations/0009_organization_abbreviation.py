from django.db import migrations, models

def add_abbrev_if_not_exists(apps, schema_editor):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='organizations_organization' AND column_name='abbreviation';")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE organizations_organization ADD COLUMN abbreviation varchar(20) DEFAULT '' NOT NULL;")

class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0008_organization_logo'),
    ]

    operations = [
        migrations.RunPython(add_abbrev_if_not_exists, reverse_code=migrations.RunPython.noop),
    ]
