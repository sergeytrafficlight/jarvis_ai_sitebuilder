import json
from django.http import FileResponse, Http404
from pathlib import Path
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from sitebuilder.settings import USER_FILES_ROOT
from core.tools import get_image_path_for_user, get_base_path_for_user
from django.utils import timezone
from .models import Profile, Transaction, SiteProject, MyTask

from .models import Profile, Transaction, SiteProject
from .tools import is_valid_http_url
from .screenshot import generate_screenshort
from core.task import run_tasks
from django.urls import reverse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404


from core.task_wrapper import task_generate_site_name_classification, task_generate_site

from core.log import *
logger.setLevel(logging.DEBUG)


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html")


@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)

    # показываем только неархивные сайты
    qs = SiteProject.objects.filter(user=request.user).exclude(status=SiteProject.STATUS_ARCHIVED)

    paginator = Paginator(qs, 10)  # 10 сайтов на страницу
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "dashboard.html", {
        "profile": profile,
        "page_obj": page_obj,
    })

@login_required
@require_POST
def site_archive(request, site_id: int):
    site = get_object_or_404(SiteProject, id=site_id, user=request.user)
    if site.status != SiteProject.STATUS_ARCHIVED:
        site.status = SiteProject.STATUS_ARCHIVED
        site.save(update_fields=["status"])
    return JsonResponse({"status": True, "id": site_id})

@login_required
@require_POST
def sites_bulk_archive(request):
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"status": False, "error": "Invalid JSON"}, status=400)

    ids = data.get("ids") or []
    if not isinstance(ids, list):
        return JsonResponse({"status": False, "error": "ids must be a list"}, status=400)

    try:
        ids = [int(i) for i in ids]
    except Exception:
        return JsonResponse({"status": False, "error": "ids must be list of integers"}, status=400)

    # Обновляем только ваши сайты и только неархивные
    updated = SiteProject.objects.filter(
        user=request.user, id__in=ids
    ).exclude(status=SiteProject.STATUS_ARCHIVED).update(status=SiteProject.STATUS_ARCHIVED)

    return JsonResponse({"status": True, "updated": updated, "ids": ids})




@login_required
def billing_history(request):
    operations = Transaction.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "billing_history.html", {"operations": operations})


class TopupForm(forms.Form):
    amount = forms.DecimalField(min_value=1, max_digits=10, decimal_places=2, label=_lazy("Сумма пополнения (USD)"))


@login_required
def topup(request):
    if request.method == "POST":
        form = TopupForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            # Here we only redirect to a placeholder payment gateway page
            return redirect(f"/payments/redirect/?amount={amount}")
        else:
            messages.error(request, _("Пожалуйста, исправьте ошибки в форме."))
    else:
        form = TopupForm()
    return render(request, "topup.html", {"form": form})


@login_required
def payment_redirect(request):
    amount = request.GET.get("amount", "0")
    return render(request, "payment_redirect.html", {"amount": amount})

@login_required
@require_POST
def reference_screenshot(request):

    data = json.loads(request.body)
    url = data.get('url')

    r, msg = is_valid_http_url(url)
    if not r:
        return JsonResponse({"status": False, "error": msg}, status=400)
    r, result = generate_screenshort(request.user, url)
    if not r:
        return JsonResponse({"status": False, "error": result}, status=400)

    img_url = result.image.url
    logger.debug(f"result image: {img_url}")

    return JsonResponse({"status": True, "img": img_url})


@login_required
def user_file_view(request, user_id, path):
    if request.user.id != user_id:
        raise Http404('File not found')
    base_path = get_base_path_for_user(request.user)
    file_path = Path(base_path + "/" + path)
    logger.debug(f"path {file_path} | {path} | {file_path}")
    return FileResponse(open(file_path, "rb"))

@login_required
@require_POST
def create_site_task(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"status": False, "error": "Invalid JSON"}, status=400)

    # Поддержим и поля из формы модалки
    prompt = (data.get("prompt") or data.get("taskPrompt") or "").strip()
    ref_url = (data.get("ref_url") or data.get("refUrl") or "").strip()
    name = (data.get("name") or "").strip()
    count = data.get("count") or data.get("siteCount") or 1

    # Валидация количества
    try:
        count = int(count)
    except Exception:
        return JsonResponse({"status": False, "error": "Некорректное количество"}, status=400)

    if count < 1 or count > 10:
        return JsonResponse({"status": False, "error": "count должен быть 1..10"}, status=400)

    # Валидация URL если указан
    if ref_url:
        ok, msg = is_valid_http_url(ref_url)
        if not ok:
            return JsonResponse({"status": False, "error": msg}, status=400)

    tasks_out = []
    base_name = name or "Сайт"
    now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    for i in range(count):
        suffix = f" #{i + 1}" if count > 1 else ""
        site = SiteProject.objects.create(
            user=request.user,
            name=f"{base_name} {now_str}{suffix}",
            promt=prompt,
            ref_site_url=ref_url,
        )

        # Запишем задачу в MyTask
        task_generate_site_name_classification(site)
        task_generate_site(site)

        async_res = run_tasks.apply_async(args=[site.id])

        tasks_out.append({"task_id": async_res.id, "site_id": site.id})

    return JsonResponse({
        "status": True,
        "tasks": tasks_out,
        "redirect_url": request.build_absolute_uri(reverse("dashboard")),
    }, status=201)







