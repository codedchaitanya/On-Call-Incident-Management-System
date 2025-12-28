from django.contrib import admin

from .models import User,OnCallSchedule,Incident,EscalationLevel
admin.site.register(Incident)
admin.site.register(User)
admin.site.register(OnCallSchedule)
admin.site.register(EscalationLevel)
