from django.urls import path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny

from .views import (
    ApiForgotPasswordView,
    ApiLoginView,
    ApiLogoutView,
    ApiMeView,
    ApiOtpRequestView,
    ApiOtpVerifyView,
    ApiRegisterView,
    HealthView,
    alerts_dashboard,
    compliance_dashboard,
    employee_ctc_history,
    employee_document_add,
    employee_document_update,
    employee_exit,
    employee_item,
    employee_onboarding_status,
    employee_profile,
    employees_collection,
    onboarding_progress,
    report_compliance_status,
    report_ctc_level_distribution,
    report_headcount,
    report_joiners_leavers,
)

schema_view = get_schema_view(
    openapi.Info(
        title='Hackathon Employee Lifecycle API',
        default_version='v1',
        description='Employee CRUD management APIs with lifecycle tracking (active/exited).',
    ),
    public=True,
    permission_classes=[AllowAny],
)

urlpatterns = [
    path('', HealthView.as_view(), name='health'),
    path('api/employees', employees_collection, name='employees_collection'),
    path('api/employees/<int:emp_id>', employee_item, name='employee_item'),
    path('api/employees/<int:emp_id>/profile', employee_profile, name='employee_profile'),
    path('api/employees/<int:emp_id>/exit', employee_exit, name='employee_exit'),
    path('api/employees/<int:emp_id>/onboarding', employee_onboarding_status, name='employee_onboarding_status'),
    path('api/employees/<int:emp_id>/documents', employee_document_add, name='employee_document_add'),
    path('api/employees/<int:emp_id>/documents/<int:doc_id>', employee_document_update, name='employee_document_update'),
    path('api/employees/<int:emp_id>/ctc-history', employee_ctc_history, name='employee_ctc_history'),
    path('api/onboarding/progress', onboarding_progress, name='onboarding_progress'),
    path('api/compliance/dashboard', compliance_dashboard, name='compliance_dashboard'),
    path('api/alerts', alerts_dashboard, name='alerts_dashboard'),
    path('api/reports/headcount', report_headcount, name='report_headcount'),
    path('api/reports/joiners-leavers', report_joiners_leavers, name='report_joiners_leavers'),
    path('api/reports/ctc-level-distribution', report_ctc_level_distribution, name='report_ctc_level_distribution'),
    path('api/reports/compliance-status', report_compliance_status, name='report_compliance_status'),
    path('api/login', ApiLoginView.as_view(), name='api_login'),
    path('api/register', ApiRegisterView.as_view(), name='api_register'),
    path('api/forgot-password', ApiForgotPasswordView.as_view(), name='api_forgot_password'),
    path('api/otp/request', ApiOtpRequestView.as_view(), name='api_otp_request'),
    path('api/otp/verify', ApiOtpVerifyView.as_view(), name='api_otp_verify'),
    path('api/home', ApiMeView.as_view(), name='api_home'),
    path('api/logout', ApiLogoutView.as_view(), name='api_logout'),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema_json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema_swagger_ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema_redoc'),
]
