import json

from django.test import TestCase
from core.tests.tools import create_profile, create_site, create_sub_site, create_ai_model_settings
from ai.ai import ai_processor_register, ai_processor_get_default_config, AI_TYPE_PROCESSOR_TXT_IMG_2_TXT, AI_TYPE_PROCESSOR_TXT_2_IMG
from ai.ai import ai_answer
from decimal import Decimal
from core.task import run_tasks_ex
from core.tests.tools import restore_ai_settings
from core.task_wrapper import (
    task_generate_site_name_classification,
    task_generate_site
)

class TasksGenerateSiteNameTest(TestCase):

    def setUp(self):
        super().setUp()
        restore_ai_settings()

    def test_task_generate_site_name_classification(self):

        engine = 'myengine'
        ai_settings = create_ai_model_settings(engine=engine)

        def _get_text_img2text_answer(prompt: str = None, img_path: str = None, creative_enabled=False) -> str:
            answer = ai_answer(
                ai_settings=ai_settings,
                answer="_get_text_img2text_answer",
                prompt_tokens=0,
                completion_tokens=0,
            )
            return answer


        p = create_profile()
        s = create_site(p)
        ss = create_sub_site(s)


        ai_processor_register(AI_TYPE_PROCESSOR_TXT_IMG_2_TXT, ai_settings.engine, _get_text_img2text_answer)
        cfg = ai_processor_get_default_config()
        cfg[AI_TYPE_PROCESSOR_TXT_IMG_2_TXT] = ai_settings.engine

        task_generate_site_name_classification(ss, cfg)
        run_tasks_ex(ss.id)

        s.refresh_from_db()
        self.assertEqual(s.name, _get_text_img2text_answer().answer)




class TasksGenerateSiteTest(TestCase):

    def setUp(self):
        super().setUp()
        restore_ai_settings()

    def test_task_generate_site(self):

        engine = 'myengine'
        ai_settings = create_ai_model_settings(engine=engine)

        def _get_text_img2text_answer(prompt: str = None, img_path: str = None, creative_enabled=False) -> str:

            r = []
            r.append({
                'file_operation': 'create',
                'file_path': './index.html',
                'text':
                '''
                <html>
                <body>
                HELLO! <br>
                <a href="./index2.html">index2</a> <br>
                <img src="img/img1.png"><br>
                </body>
                </html>
                ''',
            })

            r.append({
                'file_operation': 'create',
                'file_path': './index2.html',
                'text':
                    '''
                    <html>
                    <body>
                    HELLO! <br>
                    <a href="./index.html">index</a>
                    <img src="img/img1.png"><br>
                    </body>
                    </html>
                    ''',
            })

            r.append({
                'file_operation': 'create',
                'file_path': './index3.html',
                'text': 'delete me',
            })

            r.append({
                'file_operation': 'delete',
                'file_path': './index3.html',
            })

            r.append({
                'file_operation': 'create',
                'file_path': './img/img1.png',
                'text':
                    '''
                    ''',
                'prompt': 'img1.png',
            })

            answer = ai_answer(
                ai_settings=ai_settings,
                answer=json.dumps(r),
                prompt_tokens=0,
                completion_tokens=0,
            )
            return answer

        def _get_text2img_answer(
                prompt: str,
                input_image_path: str,
                creative_enabled=False,
        ):
            print(f"PROMPT: {prompt}")

        p = create_profile()
        s = create_site(p)
        ss = create_sub_site(s)
        ai_processor_register(AI_TYPE_PROCESSOR_TXT_IMG_2_TXT, ai_settings.engine, _get_text_img2text_answer)
        ai_processor_register(AI_TYPE_PROCESSOR_TXT_2_IMG, ai_settings.engine, _get_text2img_answer)
        cfg = ai_processor_get_default_config()
        cfg[AI_TYPE_PROCESSOR_TXT_IMG_2_TXT] = ai_settings.engine

        task_generate_site(ss, "test_prompt", cfg)
        run_tasks_ex(ss.id)




