from django.contrib.auth import views as auth_views

from .audit import audit_event


class AuditPasswordResetView(auth_views.PasswordResetView):
    def form_valid(self, form):
        email = form.cleaned_data['email']
        users = list(form.get_users(email))
        audit_event(
            'password_reset_requested',
            request=self.request,
            target=users[0] if users else None,
            outcome='success',
            email=email,
            account_exists=bool(users),
        )
        return super().form_valid(form)


class AuditPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    def form_valid(self, form):
        response = super().form_valid(form)
        audit_event(
            'password_reset_completed',
            request=self.request,
            actor=self.user,
            target=self.user,
            outcome='success',
        )
        return response
