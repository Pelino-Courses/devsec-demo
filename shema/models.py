from django.db import models

class RoleBasedAccess(models.Model):
    """
    A dummy model used exclusively to register role-based access control
    permissions into the Django contenttypes system without creating tables.
    """
    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ('view_instructor_dashboard', 'Can view instructor dashboard'),
        ]
