from core.models import SiteProject, MyTask

def task_generate_site_name_classification(site: SiteProject):
    return MyTask.objects.create(
        site=site,
        type=MyTask.TYPE_GENERATE_NAME,
        status="PENDING",
    )

def task_generate_site(site: SiteProject):
    return MyTask.objects.create(
        site=site,
        type=MyTask.TYPE_GENERATE_SITE,
        status="PENDING",
    )

def task_generate_image(site: SiteProject):
    return MyTask.objects.create(
        site=site,
        type=MyTask
    )