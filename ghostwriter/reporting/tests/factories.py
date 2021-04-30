# 3rd Party Libraries
import factory


class FindingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.Finding"
        django_get_or_create = ("title",)
