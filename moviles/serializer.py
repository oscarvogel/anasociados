from os import read
from rest_framework import serializers
from syh.models import Cliente
from syh.serializers import ClientesSerializer
from .models import CargaCombustible, Movil, Personal, TipoVencimientos, Vencimientos

class MovilSerializer(serializers.ModelSerializer):
    
    empresa = ClientesSerializer(read_only=True)
    
    class Meta:
        model = Movil
        fields = '__all__'
        
class TipoVencimientosSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoVencimientos
        fields = '__all__'        

class VencimientosSerializer(serializers.ModelSerializer):
    
    movil = serializers.PrimaryKeyRelatedField(queryset=Movil.objects.all())
    tipo_vencimiento = serializers.PrimaryKeyRelatedField(queryset=TipoVencimientos.objects.all())
    movil_patente = serializers.SerializerMethodField()
    tipo_vencimiento_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = Vencimientos
        fields = '__all__'
        
    def get_movil_patente(self, obj):
        return obj.movil.patente
    
    def get_tipo_vencimiento_nombre(self, obj):
        return obj.tipo_vencimiento.nombre

class PersonalSerializer(serializers.ModelSerializer):
    
    empresa = serializers.PrimaryKeyRelatedField(queryset=Cliente.objects.all())
    empresa_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Personal
        fields = '__all__'
    
    def get_empresa_nombre(self, obj):
        return obj.empresa.nombre        

    
class CargaCombustibleSerializer(serializers.ModelSerializer):
    
    movil = serializers.PrimaryKeyRelatedField(queryset=Movil.objects.all())
    chofer = serializers.PrimaryKeyRelatedField(queryset=Personal.objects.all())

    movil_patente = serializers.CharField(source='movil.patente', read_only=True)
    chofer_nombre = serializers.SerializerMethodField(read_only=True)
    
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    
    class Meta:
        model = CargaCombustible
        fields = ['id', 'fecha', 'litros', 'importe', 'km_hora', 'movil', 'movil_patente', 'chofer', 'chofer_nombre', 'tipo_combustible', 'empresa_nombre']
        
    
    def get_chofer_nombre(self, obj):
        return obj.chofer.apellido + ' ' + obj.chofer.nombre