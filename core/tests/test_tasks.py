from django.test import TestCase
from core.task_wrapper import task_generate_site_name_classification
from core.tests.tools import create_profile, create_site, create_sub_site

class TasksTest(TestCase):


    def test_task_generate_site_name_classification(self):

        p = create_profile()
        s = create_site(p)
        ss = create_sub_site(s)

        #task_generate_site_name_classification()


