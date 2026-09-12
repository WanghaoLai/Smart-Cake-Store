import unittest
from unittest.mock import MagicMock
from tortoise import Tortoise
from models import IndexTask, Admin
from agents.rag.index_tasks import IndexTaskService
from scripts.bootstrap_admin import create_initial_admin

class DeploymentRepairs(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await Tortoise.init(db_url="sqlite://:memory:",modules={"models":["models"]})
        await Tortoise.generate_schemas()
    async def asyncTearDown(self):
        await Tortoise.close_connections()
    async def test_exhausted_tasks_do_not_starve_new_work(self):
        await IndexTask.bulk_create([IndexTask(entity_type="goods",entity_id=i,action="delete",status="failed",attempts=3) for i in range(100)])
        task=await IndexTask.create(entity_type="goods",entity_id=101,action="delete")
        store=MagicMock()
        result=await IndexTaskService(store).run_pending(limit=100)
        self.assertEqual(result['succeeded'],1)
        self.assertEqual((await IndexTask.get(id=task.id)).status,'done')
        store.remove_goods.assert_called_once_with(101)
        self.assertEqual(await IndexTask.filter(status='failed').count(),100)
    async def test_initial_admin_never_overwrites_existing_credentials(self):
        await create_initial_admin("unique-admin","Only-Local-Setup-2026")
        original=(await Admin.all().first()).password
        with self.assertRaises(ValueError):
            await create_initial_admin("unique-admin","Another-Password-2026")
        self.assertEqual((await Admin.all().first()).password,original)
