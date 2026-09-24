"""
Tests for the core app (user model).
"""
from django.test import TestCase
from core.models import User


class UserModelTest(TestCase):
    """Tests for the custom User model."""

    def test_create_user(self):
        """Should create a user correctly."""
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.WAITER
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.role, User.Role.WAITER)
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        """Should create a superuser correctly."""
        admin = User.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@test.com'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_user_roles(self):
        """Should allow assigning different roles."""
        admin = User.objects.create_user(
            username='admin1',
            password='pass',
            role=User.Role.ADMIN
        )
        waiter = User.objects.create_user(
            username='waiter1',
            password='pass',
            role=User.Role.WAITER
        )
        kitchen = User.objects.create_user(
            username='kitchen1',
            password='pass',
            role=User.Role.KITCHEN
        )

        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertEqual(waiter.role, User.Role.WAITER)
        self.assertEqual(kitchen.role, User.Role.KITCHEN)

    def test_user_string_representation(self):
        """Should return the username as its string representation."""
        user = User.objects.create_user(
            username='testuser',
            password='pass'
        )
        self.assertEqual(str(user), 'testuser')
