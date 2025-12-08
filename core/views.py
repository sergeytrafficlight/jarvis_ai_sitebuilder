import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from django.shortcuts import get_object_or_404
from collections import defaultdict
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
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
from core.tools import get_image_path_for_user, get_base_path_for_user, get_subsite_dir, generate_uniq_subsite_dir_for_site
from .models import Profile, Transaction, SiteProject, MyTask, SubSiteProject
from django.http import FileResponse, Http404, HttpResponse
from .models import Profile, Transaction, SiteProject
from .tools import is_valid_http_url
from .screenshot import generate_screenshort
from core.task import run_tasks
from django.urls import reverse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
import requests
from pathlib import Path
from core.tools import get_subsite_dir
from core.funds_balance import balance
from .models import ImageAIEdit, ImageAIEditConversation, SubSiteProject
import os, io, zipfile
from django.utils.text import slugify
from .models import PaymentGatewaySettings, TopUpRequest
import payment.types as payment_types
import payment.cryptogator as payment_cryptogator
from core.task_wrapper import task_generate_site_name_classification, task_generate_site, task_edit_image, task_edit_site

from core.log import *
logger.setLevel(logging.DEBUG)

def trigger_error(request):
    division_by_zero = 1 / 0

def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html")


@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)

    # показываем только неархивные сайты
    qs = SiteProject.objects.filter(user=request.user).exclude(is_archived=True)

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
    site.is_archived = True
    site.save(update_fields=['is_archived'])
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
    updated = SiteProject.objects.filter(user=request.user, id__in=ids)

    for u in updated:
        u.is_archived = True
        u.save(update_fields=['is_archived'])

    return JsonResponse({"status": True})




@login_required
def billing_history(request):
    operations = Transaction.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "billing_history.html", {"operations": operations})


class TopupForm(forms.Form):
    amount = forms.DecimalField(min_value=1, max_digits=10, decimal_places=2, label=_lazy("Сумма пополнения (USD)"))


@login_required
def topup(request):
    # Подтянем доступные пары method/currency + комиссии
    settings_qs = PaymentGatewaySettings.objects.all().values("method", "currency", "commission_extra")
    settings_list = list(settings_qs)

    # Сформируем уникальные валюты и сети
    currencies = sorted({row["currency"] for row in settings_list})
    methods = sorted({row["method"] for row in settings_list})

    return render(request, "topup.html", {
        "pgs": settings_list,
        "currencies": currencies,
        "methods": methods,
    })



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
@xframe_options_sameorigin
def user_file_view(request, user_id, path):
    if request.user.id != user_id:
        raise Http404('File not found')

    base_dir = Path(get_base_path_for_user(request.user)).resolve()
    original_path = path or ""
    requested_path = (base_dir / original_path).resolve()

    # Защита от выхода за пределы директории пользователя
    try:
        requested_path.relative_to(base_dir)
    except ValueError:
        raise Http404('File not found')

    # Определяем, является ли запросом к index.html (включая запрос к директории)
    endswith_slash = original_path.endswith('/')
    is_index_request = False

    if endswith_slash:
        # Явно запросили директорию
        is_index_request = True
        requested_path = (requested_path / 'index.html')
    else:
        # Если это директория (существующая) — ищем index.html
        if requested_path.exists() and requested_path.is_dir():
            is_index_request = True
            requested_path = requested_path / 'index.html'
        # Если в пути явно указан index.html
        elif requested_path.name.lower() == 'index.html':
            is_index_request = True

    logger.debug(f"user_file_view -> base: {base_dir}, req: {requested_path}, is_index: {is_index_request}")

    try:
        return FileResponse(open(requested_path, "rb"))
    except FileNotFoundError:
        if is_index_request:
            # Возвращаем заглушку
            placeholder = """<!DOCTYPE html>
            <html lang="ru">
            <head>
              <meta charset="utf-8">
              <title>Сайт в процессе создания</title>
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <style>
                body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background:#0b1220; color:#e2e8f0; display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }
                .box { text-align:center; padding:24px; border:1px solid rgba(255,255,255,0.08); border-radius:12px; background:#0f172a; }
                .muted { color:#94a3b8; margin-top:8px; }
              </style>
            </head>
            <body>
              <div class="box">
                <h1>Сайт в процессе создания</h1>
                <div class="muted">Пожалуйста, обновите страницу позже.</div>
              </div>
            </body>
            </html>"""
            return HttpResponse(placeholder, content_type="text/html; charset=utf-8", status=200)
        # Для прочих файлов — 404
        raise Http404('File not found')


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


    base_name = name or "Сайт"
    now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    for i in range(count):
        suffix = f" #{i + 1}" if count > 1 else ""

        site = SiteProject.objects.create(
            user=request.user,
            name=f"{base_name} {now_str}{suffix}",
            prompt=prompt,
            ref_site_url=ref_url,
        )

        full_path, uniq_dir = generate_uniq_subsite_dir_for_site(site)

        sub_site = SubSiteProject.objects.create(
            site=site,
            root_sub_site=None,
            dir = uniq_dir,
        )

        # Запишем задачу в MyTask
        task_generate_site_name_classification(sub_site)
        task_generate_site(sub_site, prompt=prompt)

        run_tasks.apply_async(args=[sub_site.id])

    if count == 1:
        redirect_url = request.build_absolute_uri(
            reverse("site_detail", args=[site.id])
        )
    else:
        redirect_url = request.build_absolute_uri(reverse("dashboard"))

    return JsonResponse({
        "status": True,
        "redirect_url": redirect_url,
    }, status=201)


@login_required
def site_detail(request, site_id: int):
    site = get_object_or_404(SiteProject, id=site_id, user=request.user, is_archived=False)

    # Все сабсайты по проекту
    subs = list(SubSiteProject.objects.filter(site=site).order_by("id"))

    # Построим дерево родитель -> дети и плоский список для рендеринга с отступами
    by_parent = defaultdict(list)
    for s in subs:
        by_parent[s.root_sub_site_id].append(s)

    flat_tree = []
    def walk(pid, depth):
        for n in by_parent.get(pid, []):
            flat_tree.append({"node": n, "depth": depth, "indent": depth * 14})
            walk(n.id, depth + 1)

    walk(None, 0)

    # Выбранный сабсайт — из query ?sub=ID, либо первый в дереве
    selected_sub = None
    sub_id = request.GET.get("sub")
    if sub_id:
        try:
            selected_sub = next(s["node"] for s in flat_tree if str(s["node"].id) == str(sub_id))
        except StopIteration:
            selected_sub = None
    if not selected_sub and flat_tree:
        selected_sub = flat_tree[0]["node"]

    # Соберем iframe src (пытаемся открыть index.html выбранного сабсайта)
    iframe_src = None
    if selected_sub:
        iframe_src = reverse(
            'user_file',
            kwargs={
                'user_id': request.user.id,
                'path': f"sites/{site.id}/{selected_sub.dir}/index.html",
            }
        )


    logger.debug(f"selected_sub: {selected_sub}")
    logger.debug(f"iframe src: {iframe_src}")

    return render(request, "site_detail.html", {
        "site": site,
        "flat_tree": flat_tree,
        "selected_sub": selected_sub,
        "iframe_src": iframe_src,
    })


@login_required
def subsite_tasks_status(request, sub_id: int):
    # доступ только к своим сабсайтам
    sub = get_object_or_404(SubSiteProject, id=sub_id, site__user=request.user)

    qs = MyTask.objects.filter(sub_site=sub)
    active_qs = qs.filter(status__in=[MyTask.STATUS_AWAITING, MyTask.STATUS_PROCESSING])

    by_status = {row["status"]: row["c"] for row in qs.values("status").annotate(c=Count("id"))}

    return JsonResponse({
        "status": True,
        "active": active_qs.count(),
        "total": qs.count(),
        "site_name": sub.site.name,
        "by_status": by_status,
    })

@login_required
@require_POST
def subsite_update_text(request, sub_id: int):
    from bs4 import BeautifulSoup
    sub = get_object_or_404(SubSiteProject, id=sub_id, site__user=request.user)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"status": False, "error": "Invalid JSON"}, status=400)

    rel_path = (data.get("file") or "").strip()
    selector = (data.get("selector") or "").strip()
    new_text = data.get("text")
    if not rel_path or not selector or new_text is None:
        return JsonResponse({"status": False, "error": "Missing fields"}, status=400)

    base_dir = Path(get_subsite_dir(sub)).resolve()
    target = (base_dir / rel_path).resolve()
    try:
        target.relative_to(base_dir)
    except ValueError:
        return JsonResponse({"status": False, "error": "Invalid path"}, status=400)

    if target.suffix.lower() not in [".html", ".htm"]:
        return JsonResponse({"status": False, "error": "Only HTML files allowed"}, status=400)
    if not target.exists():
        return JsonResponse({"status": False, "error": "File not found"}, status=404)

    try:
        with open(target, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        el = soup.select_one(selector)
        if el is None:
            return JsonResponse({"status": False, "error": "Element not found by selector"}, status=404)

        # Разрешаем правку только листовых элементов (без вложенных тегов)
        if el.find(True) is not None:
            return JsonResponse({"status": False, "error": "Element has nested tags; only pure text items are editable"}, status=400)

        el.string = str(new_text)

        with open(target, "w", encoding="utf-8") as f:
            f.write(str(soup))

        return JsonResponse({"status": True})
    except Exception as e:
        logger.error("subsite_update_text error: %s", e, exc_info=True)
        return JsonResponse({"status": False, "error": "Server error"}, status=500)

@login_required
@require_POST
def subsite_replace_image(request, sub_id: int):
    sub = get_object_or_404(SubSiteProject, id=sub_id, site__user=request.user)
    rel_path = (request.POST.get("rel_path") or "").strip()
    up_file = request.FILES.get("file")

    if not rel_path or not up_file:
        return JsonResponse({"status": False, "error": "Missing rel_path or file"}, status=400)

    base_dir = Path(get_subsite_dir(sub)).resolve()
    target = (base_dir / rel_path).resolve()
    try:
        target.relative_to(base_dir)
    except ValueError:
        return JsonResponse({"status": False, "error": "Invalid path"}, status=400)

    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(target, "wb") as f:
            for chunk in up_file.chunks():
                f.write(chunk)
    except Exception as e:
        return JsonResponse({"status": False, "error": f"Write error: {e}"}, status=500)

    file_url = reverse(
        "user_file",
        kwargs={
            "user_id": request.user.id,
            "path": f"sites/{sub.site.id}/{sub.dir}/{rel_path}",
        },
    )
    return JsonResponse({"status": True, "file_url": file_url})

@login_required
@require_POST
def subsite_replace_image_by_url(request, sub_id: int):
    sub = get_object_or_404(SubSiteProject, id=sub_id, site__user=request.user)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"status": False, "error": "Invalid JSON"}, status=400)

    rel_path = (data.get("rel_path") or "").strip()
    url = (data.get("url") or "").strip()

    if not rel_path or not url:
        return JsonResponse({"status": False, "error": "Missing rel_path or url"}, status=400)

    ok, msg = is_valid_http_url(url)
    if not ok:
        return JsonResponse({"status": False, "error": msg or "Invalid URL"}, status=400)

    base_dir = Path(get_subsite_dir(sub)).resolve()
    target = (base_dir / rel_path).resolve()
    try:
        target.relative_to(base_dir)
    except ValueError:
        return JsonResponse({"status": False, "error": "Invalid path"}, status=400)

    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()
        # опционально проверим тип контента
        ctype = r.headers.get("Content-Type", "")
        if not ctype.startswith("image/"):
            return JsonResponse({"status": False, "error": "URL is not an image"}, status=400)

        with open(target, "wb") as f:
            for chunk in r.iter_content(1024 * 64):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        return JsonResponse({"status": False, "error": f"Download error: {e}"}, status=400)

    file_url = reverse(
        "user_file",
        kwargs={
            "user_id": request.user.id,
            "path": f"sites/{sub.site.id}/{sub.dir}/{rel_path}",
        },
    )
    return JsonResponse({"status": True, "file_url": file_url})

@login_required
def image_ai_conversations(request, sub_id: int):
    sub = get_object_or_404(SubSiteProject, id=sub_id, site__user=request.user)
    rel_path = (request.GET.get("rel_path") or "").strip()
    if not rel_path:
        return JsonResponse({"status": False, "error": "Missing rel_path"}, status=400)

    image, _ = ImageAIEdit.objects.get_or_create(sub_site=sub, file_path=rel_path)
    qs = ImageAIEditConversation.objects.filter(image_ai_edit=image).order_by("-created_at")

    items = []
    has_active = False
    for conv in qs:
        if conv.get_status() in [MyTask.STATUS_AWAITING, MyTask.STATUS_PROCESSING]:
            has_active = True
        items.append({
            "id": conv.id,
            "created_at": timezone.localtime(conv.created_at).isoformat(),
            "prompt": conv.prompt,
            "comment": conv.comment or "",
            "status": conv.get_status(),
        })

    return JsonResponse({
        "status": True,
        "image_id": image.id,
        "has_active": has_active,
        "items": items,  # уже в порядке: новые сверху
    })

@login_required
@require_POST
def image_ai_create(request, sub_id: int):
    sub = get_object_or_404(SubSiteProject, id=sub_id, site__user=request.user)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"status": False, "error": "Invalid JSON"}, status=400)

    has_active_tasks = MyTask.objects.filter(
        sub_site=sub,
        status__in=[MyTask.STATUS_AWAITING, MyTask.STATUS_PROCESSING]
    ).exists()
    if has_active_tasks:
        return JsonResponse({"status": False, "error": "Ожидайте завершения других задач"}, status=400)


    rel_path = (data.get("rel_path") or "").strip()
    prompt = (data.get("prompt") or "").strip()

    if not rel_path or not prompt:
        return JsonResponse({"status": False, "error": "Missing rel_path or prompt"}, status=400)


    image, _ = ImageAIEdit.objects.get_or_create(sub_site=sub, file_path=rel_path)

    has_active = ImageAIEditConversation.objects.filter(
        image_ai_edit=image,
    )
    for i in has_active:
        if i.get_status() in [MyTask.STATUS_AWAITING, MyTask.STATUS_PROCESSING]:
            return JsonResponse({"status": False, "error": "Есть незавершённые коммуникации"}, status=400)

    conv = ImageAIEditConversation.objects.create(
        image_ai_edit=image,
        prompt=prompt,
    )

    task_edit_image(sub, conv)

    run_tasks.apply_async(args=[sub.id])

    return JsonResponse({
        "status": True,
        "item": {
            "id": conv.id,
            "created_at": timezone.localtime(conv.created_at).isoformat(),
            "prompt": conv.prompt,
            "comment": conv.comment or "",
            "status": conv.get_status(),
        }
    }, status=201)


@login_required
def site_tasks_status(request, site_id: int):
  site = get_object_or_404(SiteProject, id=site_id, user=request.user)

  qs = MyTask.objects.filter(sub_site__site=site)
  by_status = {row["status"]: row["c"] for row in qs.values("status").annotate(c=Count("id"))}
  active_qs = qs.filter(status__in=[MyTask.STATUS_AWAITING, MyTask.STATUS_PROCESSING])

  return JsonResponse({
      "status": True,
      "total": qs.count(),
      "active": active_qs.count(),
      "by_status": by_status,
      'name': site.name,
  })


@login_required
def subsite_download(request, sub_id: int):
    sub = get_object_or_404(SubSiteProject, id=sub_id, site__user=request.user)

    base_dir = Path(get_subsite_dir(sub)).resolve()
    if not base_dir.exists():
        raise Http404("Subsite directory not found")

    safe_site_name = slugify(sub.site.name) or f"site-{sub.site.id}"
    dt = timezone.localtime(sub.created_at).strftime("%Y-%m-%d_%H-%M")
    zip_name = f"{safe_site_name}_{dt}.zip"

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(base_dir):
            for fname in files:
                full = os.path.join(root, fname)
                arcname = os.path.relpath(full, start=base_dir)
                zf.write(full, arcname)
    mem.seek(0)
    return FileResponse(mem, as_attachment=True, filename=zip_name, content_type="application/zip")


@login_required
def site_download_latest(request, site_id: int):
    site = get_object_or_404(SiteProject, id=site_id, user=request.user)
    sub = SubSiteProject.objects.filter(site=site).order_by("-created_at").first()
    if not sub:
        raise Http404("No subsites for this site")
    return subsite_download(request, sub.id)

@login_required
@require_POST
def site_correction_submit(request, site_id: int):
    # Проверяем, что сайт принадлежит пользователю
    site = get_object_or_404(SiteProject, id=site_id, user=request.user)

    logger.debug("site_correction_submit")
    # Поддерживаем JSON и form-data
    prompt = ""
    sub_id = None

    if request.content_type and "application/json" in request.content_type:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            payload = {}
        prompt = (payload.get("prompt") or "").strip()
        sub_id = payload.get("sub_id")
        current_url = (payload.get("current_url") or "").strip()
        current_rel_path = (payload.get("current_rel_path") or "").strip()
    else:
        prompt = (request.POST.get("prompt") or "").strip()
        sub_id = request.POST.get("sub_id")
        current_url = (request.POST.get("current_url") or "").strip()
        current_rel_path = (request.POST.get("current_rel_path") or "").strip()

    if not prompt:
        return JsonResponse({"ok": False, "error": "Текст запроса пустой"}, status=400)

    # Если передали sub_id — можно (опционально) убедиться, что он принадлежит этому сайту
    # и текущему пользователю. Логику ниже можете расширить под свою задачу.
    if sub_id:
        try:
            sub_id_int = int(sub_id)
        except Exception:
            return JsonResponse({"ok": False, "error": "Некорректный sub_id"}, status=400)

        from .models import SubSiteProject
        sub = SubSiteProject.objects.filter(id=sub_id_int, site=site).first()
        if not sub:
            return JsonResponse({"ok": False, "error": "Subsite не найден"}, status=404)


    if sub.has_active_tasks():
        return JsonResponse({"ok": False, "error": "Subsite имеет активные задачи"}, status=404)


    print(f"sub: {sub}, url: {current_url} rel: {current_rel_path}")
    task_edit_site(sub, prompt, current_url, current_rel_path)
    run_tasks.apply_async(args=[sub.id])

    return JsonResponse({
        "ok": True,
        "message": "Запрос принят",
        "site_id": site_id,
        "sub_id": sub_id
    })


@login_required
def subsite_tasks_list(request, sub_id: int):
    sub = get_object_or_404(SubSiteProject, id=sub_id, site__user=request.user)
    qs = MyTask.objects.filter(
        sub_site=sub,
        status__in=[MyTask.STATUS_AWAITING, MyTask.STATUS_PROCESSING, MyTask.STATUS_ERROR]
    ).order_by("-created_at")
    items = []
    for t in qs:
        items.append({
            "id": t.id,
            "name": t.name or "",
            "type": t.type,
            "type_label": t.get_type_display(),
            "status": t.status,
            "status_label": t.get_status_display(),
            "message": t.message or "",
            "created_at": timezone.localtime(t.created_at).isoformat(),
            "updated_at": timezone.localtime(t.updated_at).isoformat(),
        })
    return JsonResponse({"status": True, "items": items})

@login_required
@require_POST
def task_restart_stub(request, task_id: int):
    # Проверка доступа
    _ = get_object_or_404(MyTask, id=task_id, sub_site__site__user=request.user)
    # Заглушка: здесь позже будет логика рестарта
    return JsonResponse({"status": True, "message": "Restart stub OK"})

@login_required
@require_POST
def task_delete_stub(request, task_id: int):
    # Проверка доступа
    task = get_object_or_404(MyTask, id=task_id, sub_site__site__user=request.user)
    if task.status != MyTask.STATUS_ERROR:
        return JsonResponse({"status": False, "message": f"Unexpected task status {task.status}"})

    task.delete()

    # Заглушка: здесь позже будет логика удаления
    return JsonResponse({"status": True, "message": "Delete stub OK"})

@login_required
@require_POST
def site_rename(request, site_id: int):
  site = get_object_or_404(SiteProject, id=site_id, user=request.user)
  try:
      if request.content_type and "application/json" in request.content_type:
          data = json.loads(request.body or "{}")
          new_name = (data.get("name") or "").strip()
      else:
          new_name = (request.POST.get("name") or "").strip()
  except Exception:
      return JsonResponse({"status": False, "error": "Invalid JSON"}, status=400)

  if not new_name:
      return JsonResponse({"status": False, "error": "Имя не должно быть пустым"}, status=400)
  if len(new_name) > 120:
      return JsonResponse({"status": False, "error": "Имя слишком длинное (макс. 120)"}, status=400)

  old_name = site.name
  site.name = new_name
  site.save(update_fields=["name"])
  return JsonResponse({"status": True, "id": site.id, "name": site.name, "old_name": old_name})


@require_POST
def payment_receive_topup(request, gateway: str, topup_request_id: int):
    logger.debug(f"receive topup gw: {gateway}, topup_request_id: {topup_request_id}")

    try:
        data = json.loads(request.body or "{}")
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=400)

    try:
        payment_cryptogator.webhook(data, topup_request_id)
        return HttpResponse("OK", status=200)
    except Exception as e:
        logger.error(f"topup_request_id: {topup_request_id}, error: {str(e)} : post_data: {data}", payment_gateway=gateway)
        return HttpResponse(f"Error: {str(e)}", status=400)



@login_required
def topup_requests(request):
    threshold_time = timezone.now() + timedelta(minutes=30)
    qs = TopUpRequest.objects.select_related('payment_gateway_settings').filter(
        user=request.user,
        status=TopUpRequest.STATUS_AWAITING,
        expired_at__gte=threshold_time
    ).order_by("-created_at")
    # Параметры управления UI
    open_id = request.GET.get("open")
    msg = request.GET.get("msg")

    return render(request, "topup_requests.html", {
        "items": qs,
        "open_id": open_id,
        "message": msg,
    })


@login_required
@require_POST
def topup_create(request):
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"status": False, "error": "Invalid JSON"}, status=400)

    currency = (data.get("currency") or "").strip()
    method = (data.get("method") or "").strip()
    disclaimer_ok = bool(data.get("disclaimer"))

    if not currency or not method:
        return JsonResponse({"status": False, "error": "Не выбраны валюта или сеть"}, status=400)
    if not disclaimer_ok:
        return JsonResponse({"status": False, "error": "Необходимо подтвердить условия"}, status=400)

    # Валидация по PaymentGatewaySettings
    pgs = PaymentGatewaySettings.objects.filter(currency=currency, method=method, enabled=True).order_by('?').first()
    if not pgs:
        return JsonResponse({"status": False, "error": "Недоступная комбинация валюты и сети"}, status=400)

    # Если уже есть активные запросы в ожидании — отправим на страницу списка с сообщением
    threshold_time = timezone.now() + timedelta(minutes=30)
    exists = TopUpRequest.objects.filter(
        user=request.user,
        status=TopUpRequest.STATUS_AWAITING,
        payment_gateway_settings__currency=currency,
        payment_gateway_settings__method=method,
        expired_at__gte=threshold_time,
    ).exists()

    if exists:
        url = reverse("topup_requests")
        url += "?msg=" + "Воспользуйтесь переводом на один из ранее созданных запросов"
        return JsonResponse({"status": True, "redirect": url})

    if pgs.type == payment_types.GATEWAY_CRYPTOGATOR:

        topup = payment_cryptogator.get_topup(request.user, pgs)
    else:
        raise Exception(f"Unknown payment type: {pgs.type}")


    # Редирект на список активных запросов и открытие модалки
    url = reverse("topup_requests") + f"?open={topup.id}"
    return JsonResponse({"status": True, "redirect": url})


@login_required
def topup_request_status(request, request_id):
    obj = get_object_or_404(TopUpRequest, id=request_id, user=request.user)

    if obj.status == TopUpRequest.STATUS_AWAITING:
        obj = payment_cryptogator.recheck_topup_request(obj)


    now = timezone.now()
    expires_in = 0
    if obj.expired_at:
        expires_in = max(0, int((obj.expired_at - now).total_seconds()))

    if obj.status != TopUpRequest.STATUS_AWAITING:
        expires_in = None
        obj.wallet_to_pay_address = None


    amount_received = None
    if obj.topup_transaction_id:
        amount_received = str(obj.topup_transaction.amount_client)

    data = {
        "status": True,
        "item": {
            "id": str(obj.id),
            "status": obj.status,
            "provider": obj.payment_gateway_settings.type,
            "method": obj.payment_gateway_settings.method,
            "currency": obj.payment_gateway_settings.currency,
            "wallet_to_pay_address": obj.wallet_to_pay_address or "",
            "amount_min_for_order": str(obj.amount_min_for_order or ""),
            "commission_extra": obj.payment_gateway_settings.commission_extra,
            "created_at": timezone.localtime(obj.created_at).isoformat(),
            "expired_at": timezone.localtime(obj.expired_at).isoformat() if obj.expired_at else None,
            "expires_in": expires_in,
            "amount_received": amount_received,
        }
    }
    return JsonResponse(data)
