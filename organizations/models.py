from django.db import models

class Organization(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('marked_for_deletion', 'Marked for Deletion'),
    ]

    THEME_CHOICES = [
        ('pink', 'CSG Vibrant Pink'),
        ('blue', 'Ocean Blue'),
        ('emerald', 'Emerald Green'),
        ('purple', 'Royal Purple'),
        ('amber', 'Sunset Amber'),
        ('teal', 'Cyber Teal'),
        ('crimson', 'Crimson Rose'),
        ('indigo', 'Electric Indigo'),
        ('coral', 'Coral Sunset'),
        ('forest', 'Deep Forest'),
        ('nordic', 'Nordic Frost'),
        ('sapphire', 'Sapphire Velvet'),
        ('amethyst', 'Amethyst Dusk'),
        ('rosegold', 'Rose Gold Lux'),
        ('monochrome', 'Slate Monochrome'),
        ('neon', 'Neon Cyber'),
        ('cherry', 'Sakura Cherry'),
    ]

    name = models.CharField(max_length=255, unique=True)
    abbreviation = models.CharField(max_length=20, blank=True, default='')
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='org_logos/', blank=True, null=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending', db_index=True)
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='pink')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    marked_for_deletion_at = models.DateTimeField(null=True, blank=True)

    @property
    def short_name(self):
        if self.abbreviation:
            return self.abbreviation
        return self.name[:3].upper() if self.name else "CSG"

    @property
    def display_name(self):
        if self.abbreviation and self.abbreviation.upper() not in self.name.upper():
            return f"{self.name} ({self.abbreviation})"
        return self.name

    def __str__(self):
        if self.abbreviation:
            return f"{self.name} ({self.abbreviation})"
        return self.name

    class Meta:
        ordering = ['name']
