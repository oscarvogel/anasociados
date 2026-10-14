from django.shortcuts import get_object_or_404, render
import json
from collections import defaultdict
from datetime import datetime

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse

from .forms import UserUpdateForm
from .management_forms import AreaAssignmentFormSet, UserManagementForm
from .models import AreasProfile, Profile, UsuarioIngreso, UsuarioMenuAcceso
from syh.models import Area, Cliente

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


@login_required(login_url='/admin/login/')
def management_users(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Solo un superusuario puede gestionar usuarios.")

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("estado", "")
    client_filter = request.GET.get("cliente", "")

    users = (
        User.objects.filter(is_superuser=False)
        .select_related("profile__cliente")
        .prefetch_related(
            Prefetch(
                "areasprofile_set",
                queryset=AreasProfile.objects.select_related("area").order_by("area__detalle"),
            )
        )
        .order_by("username")
    )

    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(profile__cliente__nombre__icontains=query)
            | Q(areasprofile__area__detalle__icontains=query)
        ).distinct()
    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)
    if client_filter:
        users = users.filter(profile__cliente_id=client_filter)

    return render(
        request,
        "pages/usuarios/management_users.html",
        {
            "users": users,
            "query": query,
            "status_filter": status_filter,
            "client_filter": client_filter,
            "clients": Cliente.objects.order_by("nombre"),
        },
    )


@login_required(login_url='/admin/login/')
def management_user_edit(request, user_id=None):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Solo un superusuario puede gestionar usuarios.")

    target_user = None
    if user_id is not None:
        target_user = get_object_or_404(User, pk=user_id)
        if target_user.is_superuser:
            return HttpResponseForbidden("Las cuentas superusuario no se editan desde esta pantalla.")

    user_form = UserManagementForm(
        data=request.POST if request.method == "POST" else None,
        instance=target_user,
    )
    selected_client_id = (
        request.POST.get("cliente") if request.method == "POST" else user_form["cliente"].value()
    )
    selected_client = Cliente.objects.filter(pk=selected_client_id).first() if selected_client_id else None

    initial_assignments = []
    if request.method != "POST" and target_user is not None:
        initial_assignments = list(
            AreasProfile.objects.filter(user=target_user)
            .select_related("area")
            .order_by("area__detalle")
            .values("area_id", "telefono_whatsapp")
        )
        initial_assignments = [
            {"area": item["area_id"], "telefono_whatsapp": item["telefono_whatsapp"]}
            for item in initial_assignments
        ]

    area_formset = AreaAssignmentFormSet(
        data=request.POST if request.method == "POST" else None,
        initial=initial_assignments,
        prefix="areas",
        form_kwargs={"cliente": selected_client},
    )

    if request.method == "POST" and user_form.is_valid() and area_formset.is_valid():
        client = user_form.cleaned_data["cliente"]
        assignments = []
        for form in area_formset.forms:
            cleaned_data = form.cleaned_data
            if cleaned_data.get("DELETE"):
                continue
            area = cleaned_data.get("area")
            if area is None:
                continue
            if area.cliente_id != client.pk:
                form.add_error("area", "El área debe pertenecer a la empresa seleccionada.")
                break
            assignments.append((area, cleaned_data.get("telefono_whatsapp", "")))

        if not any(form.errors for form in area_formset.forms):
            with transaction.atomic():
                user = user_form.save(commit=False)
                password = user_form.cleaned_data.get("password1")
                if password:
                    user.set_password(password)
                user.save()

                Profile.objects.update_or_create(
                    user=user,
                    defaults={"cliente": client},
                )

                existing_by_area = {}
                existing_assignments = AreasProfile.objects.filter(user=user).order_by("pk")
                for existing in existing_assignments:
                    if existing.area_id in existing_by_area:
                        existing.delete()
                    else:
                        existing_by_area[existing.area_id] = existing

                retained_ids = []
                for area, telefono in assignments:
                    existing = existing_by_area.pop(area.pk, None)
                    if existing:
                        existing.telefono_whatsapp = telefono
                        existing.save(update_fields=("telefono_whatsapp",))
                        retained_ids.append(existing.pk)
                    else:
                        created = AreasProfile.objects.create(
                            user=user,
                            area=area,
                            telefono_whatsapp=telefono,
                        )
                        retained_ids.append(created.pk)

                AreasProfile.objects.filter(user=user).exclude(pk__in=retained_ids).delete()

            messages.success(request, "El usuario se guardó correctamente.")
            return redirect("usuarios:management_users")

    client_areas = defaultdict(list)
    for area in Area.objects.order_by("cliente_id", "detalle"):
        client_areas[str(area.cliente_id)].append({"id": str(area.pk), "label": area.detalle})

    return render(
        request,
        "pages/usuarios/management_user_form.html",
        {
            "user_form": user_form,
            "area_formset": area_formset,
            "client_areas": dict(client_areas),
            "editing_user": target_user,
            "list_url": reverse("usuarios:management_users"),
        },
    )
