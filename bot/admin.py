from django.contrib import admin
from .models import (PersonalOrder, TelegramUser,
                     Region, Area, City,
                     DeliveryCompany, OutletLocation, GroupOrder)

admin.site.register(TelegramUser)
admin.site.register(PersonalOrder)
admin.site.register(Region)
admin.site.register(Area)
admin.site.register(City)
admin.site.register(DeliveryCompany)
admin.site.register(OutletLocation)
admin.site.register(GroupOrder)
