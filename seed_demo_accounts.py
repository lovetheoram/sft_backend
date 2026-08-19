# Seed script to ensure demo building, flats, and demo accounts exist in Django DB
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src_backend.settings')
django.setup()

from Finance.models import Building, Flat, User, Member

def seed():
    print("--- Seeding Demo Accounts & Building Structure ---")

    # 1. Ensure demoBuilding exists
    building, created = Building.objects.get_or_create(
        name="demoBuilding",
        defaults={"address": "123 Demo Society Avenue"}
    )
    if created:
        print("  [SUCCESS] Created Building: demoBuilding")
    else:
        print("  [INFO] Building demoBuilding already exists")

    # 2. Ensure demoFlat 1 and demoFlat 2 exist
    flat1, created1 = Flat.objects.get_or_create(
        building=building,
        number="demoFlat 1",
        defaults={"is_occupied": True}
    )
    if created1:
        print("  [SUCCESS] Created Flat: demoFlat 1")
    else:
        print("  [INFO] Flat demoFlat 1 already exists")

    flat2, created2 = Flat.objects.get_or_create(
        building=building,
        number="demoFlat 2",
        defaults={"is_occupied": True}
    )
    if created2:
        print("  [SUCCESS] Created Flat: demoFlat 2")
    else:
        print("  [INFO] Flat demoFlat 2 already exists")

    # 3. Ensure demoAdmin (Super Admin) exists
    user_admin, created_admin = User.objects.get_or_create(
        username="demoAdmin",
        defaults={
            "email": "demoadmin@sft.com",
            "first_name": "Demo",
            "last_name": "SuperAdmin",
            "role": "admin",
            "flat": None,
            "phone": "9876543210"
        }
    )
    if created_admin:
        user_admin.set_password("demo12345")
        user_admin.save()
        print("  [SUCCESS] Created User: demoAdmin (Super Admin)")
    else:
        user_admin.set_password("demo12345")
        user_admin.save()
        print("  [INFO] Updated password for demoAdmin")

    # 4. Ensure demoBuildingAdmin (Building Admin) exists
    user_badmin, created_badmin = User.objects.get_or_create(
        username="demoBuildingAdmin",
        defaults={
            "email": "demobuildingadmin@sft.com",
            "first_name": "Demo",
            "last_name": "BldgAdmin",
            "role": "admin",
            "flat": flat1,
            "phone": "9876543211"
        }
    )
    if created_badmin:
        user_badmin.set_password("demo12345")
        user_badmin.save()
        Member.objects.get_or_create(user=user_badmin)
        print("  [SUCCESS] Created User: demoBuildingAdmin (Building Admin)")
    else:
        user_badmin.flat = flat1
        user_badmin.set_password("demo12345")
        user_badmin.save()
        Member.objects.get_or_create(user=user_badmin)
        print("  [INFO] Updated demoBuildingAdmin linked to demoFlat 1")

    # 5. Ensure demoResident (Resident) exists
    user_res, created_res = User.objects.get_or_create(
        username="demoResident",
        defaults={
            "email": "demoresident@sft.com",
            "first_name": "Demo",
            "last_name": "Resident",
            "role": "resident",
            "flat": flat2,
            "phone": "9876543212"
        }
    )
    if created_res:
        user_res.set_password("demo12345")
        user_res.save()
        Member.objects.get_or_create(user=user_res)
        print("  [SUCCESS] Created User: demoResident (Resident)")
    else:
        user_res.flat = flat2
        user_res.set_password("demo12345")
        user_res.save()
        Member.objects.get_or_create(user=user_res)
        print("  [INFO] Updated demoResident linked to demoFlat 2")

    print("\n--- Demo accounts successfully ready ---")
    print("  1. demoAdmin / demo12345 (Super Admin)")
    print("  2. demoBuildingAdmin / demo12345 (Building Admin - demoBuilding / demoFlat 1)")
    print("  3. demoResident / demo12345 (Resident - demoBuilding / demoFlat 2)")

if __name__ == '__main__':
    seed()
