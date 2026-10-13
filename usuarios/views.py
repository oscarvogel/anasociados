from django.shortcuts import render
import json
from collections import defaultdict
from datetime import datetime

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.db.models import Count
from django.utils import timezone
from django.contrib.auth.models import User

from .forms import UserUpdateForm
from .models import UsuarioIngreso, UsuarioMenuAcceso

@login_required(login_url='/admin/login/')
def user_logout(request):
    logout(request)
    return redirect('/')

@login_required
def update_user(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('/')  # Redirige al perfil del usuario después de actualizar
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'pages/usuarios/update_user.html', {'form': form})


@login_required
def reporte_accesos(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("No tenes permisos para acceder a este reporte.")

    periodo_seleccionado = request.GET.get('periodo')
    usuario_seleccionado = request.GET.get('usuario')

    usuario_seleccionado_id = None
    try:
        if usuario_seleccionado:
            usuario_seleccionado_id = int(usuario_seleccionado)
    except (TypeError, ValueError):
        usuario_seleccionado_id = None

    inicio = None
    fin = None
    if periodo_seleccionado:
        try:
            anio, mes = [int(x) for x in periodo_seleccionado.split('-')]
            inicio = datetime(anio, mes, 1)
            fin = datetime(anio + 1, 1, 1) if mes == 12 else datetime(anio, mes + 1, 1)

            if timezone.is_aware(timezone.now()):
                tz = timezone.get_current_timezone()
                inicio = timezone.make_aware(inicio, tz)
                fin = timezone.make_aware(fin, tz)
        except (ValueError, TypeError):
            periodo_seleccionado = None
            inicio = None
            fin = None

    ingresos_qs = UsuarioIngreso.objects.all()
    accesos_qs = UsuarioMenuAcceso.objects.all()

    if usuario_seleccionado_id:
        ingresos_qs = ingresos_qs.filter(user_id=usuario_seleccionado_id)
        accesos_qs = accesos_qs.filter(user_id=usuario_seleccionado_id)

    ingresos_por_periodo = defaultdict(lambda: {"total_ingresos": 0, "usuarios": set()})
    for fecha_hora, user_id in ingresos_qs.values_list('fecha_hora', 'user_id'):
        periodo = fecha_hora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ingresos_por_periodo[periodo]["total_ingresos"] += 1
        ingresos_por_periodo[periodo]["usuarios"].add(user_id)

    resumen_ingresos = []
    for periodo in sorted(ingresos_por_periodo.keys(), reverse=True):
        bucket = ingresos_por_periodo[periodo]
        resumen_ingresos.append(
            {
                "periodo": periodo,
                "total_ingresos": bucket["total_ingresos"],
                "usuarios_unicos": len(bucket["usuarios"]),
            }
        )

    accesos_menus = accesos_qs
    if inicio and fin:
        accesos_menus = accesos_menus.filter(fecha_hora__gte=inicio, fecha_hora__lt=fin)

    resumen_menus = (
        accesos_menus
        .values('menu_nombre')
        .annotate(
            total_ingresos=Count('id'),
            usuarios_unicos=Count('user', distinct=True),
        )
        .order_by('-total_ingresos', 'menu_nombre')
    )

    resumen_ingresos_lista = resumen_ingresos
    resumen_menus_lista = list(resumen_menus)

    ingresos_ordenados = list(reversed(resumen_ingresos_lista))
    chart_ingresos_labels = [
        row['periodo'].strftime('%m/%Y') if row['periodo'] else ''
        for row in ingresos_ordenados
    ]
    chart_ingresos_totales = [row['total_ingresos'] for row in ingresos_ordenados]
    chart_ingresos_usuarios = [row['usuarios_unicos'] for row in ingresos_ordenados]

    top_menus = resumen_menus_lista[:10]
    chart_menus_labels = [row['menu_nombre'] for row in top_menus]
    chart_menus_totales = [row['total_ingresos'] for row in top_menus]

    top_inicio = inicio
    top_fin = fin
    if not top_inicio or not top_fin:
        ahora = timezone.localtime(timezone.now())
        top_inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if ahora.month == 12:
            top_fin = top_inicio.replace(year=ahora.year + 1, month=1)
        else:
            top_fin = top_inicio.replace(month=ahora.month + 1)

    top_usuarios_mes = list(
        UsuarioIngreso.objects
        .filter(fecha_hora__gte=top_inicio, fecha_hora__lt=top_fin)
        .values('user__username', 'user__first_name', 'user__last_name')
        .annotate(total_ingresos=Count('id'))
        .order_by('-total_ingresos', 'user__username')[:10]
    )

    chart_top_usuarios_labels = [
        (f"{row['user__first_name']} {row['user__last_name']}".strip() or row['user__username'])
        for row in top_usuarios_mes
    ]
    chart_top_usuarios_totales = [row['total_ingresos'] for row in top_usuarios_mes]

    detalle_usuario_accesos = []
    if usuario_seleccionado_id:
        detalle_usuario_accesos = list(
            accesos_menus
            .select_related('user')
            .order_by('-fecha_hora')[:100]
        )

    periodos_disponibles = sorted(
        {
            fecha_hora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            for fecha_hora in UsuarioMenuAcceso.objects.values_list('fecha_hora', flat=True)
        },
        reverse=True,
    )

    usuarios_disponibles = User.objects.filter(
        id__in=UsuarioMenuAcceso.objects.values_list('user_id', flat=True).distinct()
    ).order_by('username')

    top_periodo_texto = top_inicio.strftime('%m/%Y') if top_inicio else ''

    return render(
        request,
        'pages/usuarios/reporte_accesos.html',
        {
            'resumen_ingresos': resumen_ingresos,
            'resumen_menus': resumen_menus,
            'detalle_usuario_accesos': detalle_usuario_accesos,
            'top_usuarios_mes': top_usuarios_mes,
            'top_periodo_texto': top_periodo_texto,
            'periodos_disponibles': periodos_disponibles,
            'periodo_seleccionado': periodo_seleccionado,
            'usuarios_disponibles': usuarios_disponibles,
            'usuario_seleccionado': str(usuario_seleccionado_id) if usuario_seleccionado_id else '',
            'chart_ingresos_labels': json.dumps(chart_ingresos_labels),
            'chart_ingresos_totales': json.dumps(chart_ingresos_totales),
            'chart_ingresos_usuarios': json.dumps(chart_ingresos_usuarios),
            'chart_menus_labels': json.dumps(chart_menus_labels),
            'chart_menus_totales': json.dumps(chart_menus_totales),
            'chart_top_usuarios_labels': json.dumps(chart_top_usuarios_labels),
            'chart_top_usuarios_totales': json.dumps(chart_top_usuarios_totales),
        },
    )
