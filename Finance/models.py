from django.db import models
from django.contrib.auth.models import AbstractUser

# --- Global constants ---
MONTH_CHOICES = [
    ("Jan", "January"), ("Feb", "February"), ("Mar", "March"),
    ("Apr", "April"), ("May", "May"), ("Jun", "June"),
    ("Jul", "July"), ("Aug", "August"), ("Sep", "September"),
    ("Oct", "October"), ("Nov", "November"), ("Dec", "December"),
]

ROLE_CHOICES = [
    ("admin", "Admin"),
    ("resident", "Resident"),
    ("staff", "Staff"),
]

class Building(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g. "Tower A"
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Flat(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='flats')
    number = models.CharField(max_length=10)  # e.g. "101", "B-2"
    is_occupied = models.BooleanField(default=False)

    class Meta:
        unique_together = ('building', 'number')

    def __str__(self):
        return f"{self.building.name} - {self.number}"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='resident')
    flat = models.OneToOneField(Flat, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    # building_admin_for = models.ForeignKey(Building, on_delete=models.SET_NULL, null=True, blank=True, related_name='admins' )


    def __str__(self):
        return f"{self.username} - {self.flat}"




# --- Member (linked to resident User) ---
class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    move_in_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.flat})"


class SpecialCharge(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)

    building = models.ForeignKey(Building,on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    amount_expected = models.IntegerField()
    due_date = models.DateField()

    def __str__(self):
        return f"{self.title} ({self.building.name})"
    

class Income(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('fraud', 'Fraud'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)  
    special_charge = models.ForeignKey(SpecialCharge,null=True,blank=True,on_delete=models.SET_NULL)
    amount = models.IntegerField()
    date = models.DateField()
    description = models.TextField(blank=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_proof = models.FileField(upload_to='payment_proofs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        base = f"{self.member.user.get_full_name()}: ₹{self.amount} ({self.date.strftime('%b-%Y')})"
        return f"Income - {base}" if not self.special_charge else f"Special - {self.special_charge.title} - {base}"


# --- Expense (e.g. water, electricity) ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)  # 🔒 Scopes category to building

    def __str__(self):
        return self.name

class Expense(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)  

    amount = models.IntegerField()
    date = models.DateField()
    description = models.TextField(blank=True)
    bill_number = models.CharField(max_length=100, blank=True, null=True)
    bill_attachment = models.FileField(upload_to='expense_bills/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def month(self):
        return self.date.strftime("%b")

    @property
    def year(self):
        return self.date.year

    def __str__(self):
        return f"Expense - {self.category.name}: ₹{self.amount} ({self.month}-{self.year})"

# --- Previous dues (legacy or unpaid) ---
class PreviousDue(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.IntegerField()
    reason = models.CharField(max_length=255)
    added_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Due - {self.member.user.get_full_name()}: ₹{self.amount} for {self.reason}"

# --- Announcements ---
class Announcement(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE,null=True,blank=True,default=1)  

    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Announcement: {self.title}"

# --- Complaints or Suggestions ---
class Complaint(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
    ]
    building = models.ForeignKey(Building, on_delete=models.CASCADE,null=True,blank=True)  

    sender= models.ForeignKey(User,on_delete=models.CASCADE,related_name='complaints_made')
    recipient = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name='complaints_received')
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} - from {self.sender.username} to {self.recipient.username if self.recipient else 'N/A'}"

    
# --- Document uploads (meeting minutes, rules, etc.) ---
class SocietyDocument(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE,null=True,blank=True,default=1)  

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    income = models.ForeignKey(Income, on_delete=models.CASCADE, null=True, blank=True)  # ✅ link to income
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"message {self.user.username}-{self.created_at}"




# try:
#     member = Member.objects.get(user__username=username)
# except Member.DoesNotExist:
#     print(f"❌ Member not found for username: {username}")
# else:
#     for i, amount in enumerate(amounts):
#         year, month = months[i]
#         Income.objects.create(
#             member=member,
#             amount=amount,
#             date=date(year, month, 1),
#             description="Imported from sheet",
#             transaction_id=f"{username}-{year}-{month:02d}",
#             status="verified"
#         )
#     print(f"✅ Income records created for user: {username}")

# for username, amounts in amounts_by_user.items():
#     try:
#         member = Member.objects.get(user__username=username)
#     except Member.DoesNotExist:
#         print(f"❌ Member not found for username: {username}")
#     else:
#         for i, amount in enumerate(amounts):
#             if amount is not None:
                
#                 year, month = months[i]
#                 Income.objects.create(
#                     member=member,
#                     amount=amount,
#                     date=date(year, month, 1),
#                     description="Imported from sheet",
#                     transaction_id=f"{username}-{year}-{month:02d}",
#                     status="verified"
#                 )
#         print(f"✅ Done for username: {username}")


# amounts_by_user = {
#     "Ajay": [
#         1300, 1300, 2600, None, None, None,3900,
#         2600, None, None, 2600, 1300
#     ],
#     "Om": [
#         1300, 1300, 1300, 1300, 1300, 1300,
#         1300, 1300, 1300, 1300, 1300, 1300
#     ],
#     "Saurav": [
#         1200, 1200, 1200, 1200, 1200, 1200,
#         1200, 1200, 2400, None, 1200, 1200
#     ],
#     "Deepak": [
#         1300, 1300, 1300, None, 2700, None,
#         None, 5100, None, 100, None, 3800
#     ],
#     "Sankar": [
#         None, None, None,4800, None, 2400, None,
#         None, None, None, None, 7200
#     ],
#     "Sujeet": [
#         1300, 1300, 1300, 1300, 1300, 1300,
#         1300, 1300, 1150, 1450, 1300, 1300
#     ],
#     "N": [
#         1200, 1200, 1100, None, 3600, None,
#         1300, 1200, 1200, 1200, 1200, 1200
#     ],
#     "T": [
#         1300, 1300, 1300, 1300, 1300, 1300,
#         1300, 1300, 1300, 1300, 1300, 1300
#     ]
# }
