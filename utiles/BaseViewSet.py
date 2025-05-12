# En un archivo como app/mixins.py o utils/drf_mixins.py

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework import viewsets
from rest_framework import filters
from rest_framework.pagination import PageNumberPagination

class StandarPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'results': data,
            'count': self.page.paginator.count,
            'current_page': self.page.number,
            'total_pages': self.page.paginator.num_pages
        })
    
class DebugSerializerErrorsMixin(CreateModelMixin, UpdateModelMixin):
    """
    Mixin para agregar impresión de errores del serializador en métodos create y update.
    """
    def create(self, request, *args, **kwargs):
        """
        Sobrescribe el método create para imprimir errores del serializador.
        """
        # Obtiene el serializador como lo haría el método original
        serializer = self.get_serializer(data=request.data)

        # Realiza la validación manualmente para interceptar los errores
        if serializer.is_valid():
            # Si es válido, llama al método create original (del mixin CreateModelMixin)
            return super().create(request, *args, **kwargs)
        else:
            # Imprimimos los errores SOLO si DEBUG es True
            if settings.DEBUG:
                # Si no es válido, imprime los errores antes de devolver la respuesta 400
                print("Errores del Serializador en CREATE:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Sobrescribe el método update para imprimir errores del serializador.
        """
        # Obtiene los datos y la instancia como lo haría el método original
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        # Realiza la validación manualmente para interceptar los errores
        if serializer.is_valid():
            # Si es válido, llama al método update original (del mixin UpdateModelMixin)
             return super().update(request, *args, **kwargs)
        else:
            if settings.DEBUG:
                # Si no es válido, imprime los errores antes de devolver la respuesta 400
                print("Errores del Serializador en UPDATE:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Puedes agregar partial_update si lo usas explícitamente y quieres depurarlo también
    # def partial_update(self, request, *args, **kwargs):
    #     kwargs['partial'] = True
    #     return self.update(request, *args, **kwargs)

class BaseAppModelViewSet(DebugSerializerErrorsMixin, viewsets.ModelViewSet):
    # Puedes poner aquí filtros comunes, paginación por defecto, etc.
    # filter_backends = [...]
    pagination_class = StandarPagination