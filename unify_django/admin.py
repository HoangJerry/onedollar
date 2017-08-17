from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model

from forms import CustomUnifyUserChangeForm, CustomUnifyUserCreationForm


class BaseModelAdmin(admin.ModelAdmin):
    """
    Base ModelAdmin that set current user as creator.
    """

    def save_model(self, request, obj, form, change):
        # set current user to creator if empty
        if not obj.creator_id:
            obj.creator = request.user

        return super(BaseModelAdmin, self).save_model(
            request, obj, form, change)


class UnifyBaseUserAdmin(UserAdmin):
    model = get_user_model
    list_display = ('email', 'first_name', 'last_name', 'dob', 'gender', 'status')
    search_fields = ('email', 'first_name', 'last_name')
    fieldsets = (
        (None, {'fields': ('status', 'email', 'password')}),
        (_('Personal info'),
         {'fields': ('first_name', 'last_name', 'avatar', 'fb_uid', 'gender',
                     'dob', 'about', 'relationship_status',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
         ),
    )
    form = CustomUnifyUserChangeForm
    add_form = CustomUnifyUserCreationForm
