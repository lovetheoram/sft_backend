from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Member, Income, Expense, Category,
    Complaint, PreviousDue, Announcement, SocietyDocument,Flat,Building
)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('username', 'email', 'first_name', 'last_name', 'flat_number', 'is_staff')

    # Make flat_number readable but not editable in user detail page
    readonly_fields = ('flat_number',)

    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('flat', 'role', 'phone')}),  # add your real fields here, e.g. flat
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('flat', 'role', 'phone')}),
    )

    def flat_number(self, obj):
        return obj.flat.number if obj.flat else "-"
    flat_number.short_description = 'Flat Number'

admin.site.register(User, UserAdmin)


admin.site.register(Member)
admin.site.register(Income)
admin.site.register(Expense)
admin.site.register(Category)
admin.site.register(Complaint)
admin.site.register(PreviousDue)
admin.site.register(Announcement)
admin.site.register(SocietyDocument)
admin.site.register(Building)
admin.site.register(Flat)
