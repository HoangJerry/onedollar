from django.contrib.auth.forms import UserCreationForm, UserChangeForm


class CustomUnifyUserCreationForm(UserCreationForm):
    """
    A form that creates a user, with no privileges, from the given email and
    password.
    """

    def __init__(self, *args, **kargs):
        super(CustomUnifyUserCreationForm, self).__init__(*args, **kargs)
        if self.fields.has_key('username'):
            del self.fields['username']


class CustomUnifyUserChangeForm(UserChangeForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """

    def __init__(self, *args, **kargs):
        super(CustomUnifyUserChangeForm, self).__init__(*args, **kargs)
        if self.fields.has_key('username'):
            del self.fields['username']

    def clean_fb_uid(self):
        fb_uid = self.cleaned_data.get('fb_uid', '').strip()
        if fb_uid == '':
            fb_uid = None
        return fb_uid
