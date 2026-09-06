from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import UserProfile


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    secteur_activite = serializers.SerializerMethodField()
    whatsapp = serializers.SerializerMethodField()
    recevoir_alertes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "groups", "permissions", "secteur_activite", "whatsapp", "recevoir_alertes"]
        read_only_fields = ["id", "role"]

    def get_role(self, obj):
        return "administrateur" if obj.is_staff else "utilisateur"

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))

    def get_permissions(self, obj):
        return sorted(obj.get_all_permissions())

    def get_profile(self, obj):
        profile, _ = UserProfile.objects.get_or_create(user=obj)
        return profile

    def get_secteur_activite(self, obj):
        return self.get_profile(obj).secteur_activite

    def get_whatsapp(self, obj):
        return self.get_profile(obj).whatsapp

    def get_recevoir_alertes(self, obj):
        return self.get_profile(obj).recevoir_alertes


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    secteur_activite = serializers.CharField(required=False, allow_blank=True, max_length=150)
    whatsapp = serializers.CharField(required=False, allow_blank=True, max_length=30)
    recevoir_alertes = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password", "password_confirm", "secteur_activite", "whatsapp", "recevoir_alertes"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Les mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        # Toute inscription publique crée volontairement un utilisateur simple.
        profile_data = {
            "secteur_activite": validated_data.pop("secteur_activite", ""),
            "whatsapp": validated_data.pop("whatsapp", ""),
            "recevoir_alertes": validated_data.pop("recevoir_alertes", True),
        }
        user = User.objects.create_user(**validated_data, is_staff=False, is_superuser=False)
        UserProfile.objects.create(user=user, **profile_data)
        return user
