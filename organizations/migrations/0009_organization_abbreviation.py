from django.db import migrations, models


def add_abbrev_if_not_exists(apps, schema_editor):
    from django.db import connection
    table_name = 'organizations_organization'
    column_name = 'abbreviation'
    
    with connection.cursor() as cursor:
        table_description = connection.introspection.get_table_description(cursor, table_name)
        columns = [col.name for col in table_description]
        
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} varchar(20) DEFAULT '' NOT NULL;")


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0008_organization_logo'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_abbrev_if_not_exists, reverse_code=migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='organization',
                    name='abbreviation',
                    field=models.CharField(blank=True, default='', max_length=20),
                ),
            ],
        ),
    ]
