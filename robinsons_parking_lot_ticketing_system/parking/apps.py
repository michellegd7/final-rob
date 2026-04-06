from django.apps import AppConfig


class ParkingConfig(AppConfig):
    name = 'parking'


class YourAppConfig(AppConfig):
    def ready(self):
        import yourapp.signals