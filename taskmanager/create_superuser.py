#!/usr/bin/env python
"""Create Django superuser from environment variables (for Render deploys without shell)."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taskmanager.settings")

    import django

    django.setup()

    from django.contrib.auth import get_user_model

    username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

    if not username or not password:
        print(
            "Skipping superuser creation: "
            "DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD are not both set."
        )
        return

    User = get_user_model()

    if User.objects.filter(username=username).exists():
        print(f"Superuser '{username}' already exists. No changes made.")
        return

    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — log and fail deploy if creation breaks
        print(f"Error creating superuser: {exc}", file=sys.stderr)
        sys.exit(1)
