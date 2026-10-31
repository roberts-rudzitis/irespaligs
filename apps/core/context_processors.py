from django.conf import settings


def site(request):
    return {"support_email": settings.SUPPORT_EMAIL, "legal_reviewed": settings.LEGAL_TEXTS_REVIEWED}
