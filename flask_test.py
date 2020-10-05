from myproject import app
import unittest

'''
unit тесты. Хотя бы частично
Нужен отдельный тестировщик
'''

class FlaskTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        # creates a test client
        self.app = app.test_client()
        # propagate the exceptions to the test client
        self.app.testing = True

    def tearDown(self):
        pass

    def test_home_status_code(self):
        # тест корня
        # корневая страница не определена и должна возвращать 404
        result = self.app.get('/')
        # assert the status code of the response
        self.assertEqual(result.status_code, 404)

    def test_any_text(self):
        result = self.app.get('/some')
        # assert the status code of the response
        self.assertEqual(str(result.data)[1:], "'Hello, some!'")

    def test_app_datchik(self):
        result = self.app.get('/app/datchik')
        # assert the status code of the response
        self.assertEqual(str(result.data)[1:], "'No device id send'")
        result = self.app.get('/app/datchik?did=40RRTM304FCdd5M80ods')
        self.assertNotEqual(str(result.data)[1:], "'No device id send'")

    def test_app_stat(self):
        result = self.app.get("/app/stat")
        # assert the status code of the response
        self.assertEqual(str(result.data)[1:], "'No device id send'")
        result = self.app.get('/app/stat?did=40RRTM304FCdd5M80ods&rid=2')
        self.assertEqual(str(result.data)[1:], "'No date send'")

    def test_app_settings(self):
        result = self.app.get("/app/settings")
        # assert the status code of the response
        self.assertEqual(str(result.data)[1:], "'No device id send'")
        result = self.app.get('/app/settings?did=40RRTM304FCdd5M80ods')
        self.assertEqual(str(result.data)[1:], "'200'")

    def test_app__scen_getcur(self):
        result = self.app.get("/app/scen/get_cur")
        # assert the status code of the response
        self.assertEqual(str(result.data)[1:], "'No device id send'")
        result = self.app.get('/app/scen/get_cur?did=40RRTM304FCdd5M80ods&rid=2')
        self.assertEqual(str(result.data)[1:], "'-1'")

    def test_app_chtemp(self):
        result = self.app.get("/app/ch_temp")
        # assert the status code of the response
        self.assertEqual(str(result.data)[1:], "'No device id send'")
        result = self.app.get('/app/ch_temp?did=40RRTM304FCdd5M80ods&rid=2&ch_temp=20')
        self.assertEqual(str(result.data)[1:], "'200'")

    def test_app_flow(self):
        result = self.app.get("/app/flow")
        # assert the status code of the response
        self.assertEqual(str(result.data)[1:], "'No device id send'")
        result = self.app.get('/app/flow?did=40RRTM304FCdd5M80ods&rid=2')
        self.assertEqual(str(result.data)[1:], "'200'")


if __name__ == '__main__':
    unittest.main()
