from rest_framework import serializers
from .models import ERBilling
from bson import ObjectId


# Custom field to handle ObjectId
class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value)
    def to_internal_value(self, data):
        return str(data)

class ERBillingSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)  # :point_left: Add this line to use custom field
    
    class Meta:
        model = ERBilling
        fields = "__all__"
