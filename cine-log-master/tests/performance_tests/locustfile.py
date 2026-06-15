from locust import HttpUser, task, between

class CineLogUser(HttpUser):
    # 模拟用户思考时间：1-3秒
    wait_time = between(1, 3)
    
    @task
    def get_records(self):
        """测试获取记录列表接口"""
        self.client.get("/api/records", name="/api/records")