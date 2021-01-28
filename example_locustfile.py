import json
import os
from locust import HttpUser, task, between

from appian_locust import AppianTaskSet

class GetFrontPageTaskSet(AppianTaskSet):
    def on_start(self):
        super().on_start()
        pass

    @task
    def get_front_page(self):
        self.client.get('/')


class UserActor(HttpUser):
    tasks = [GetFrontPageTaskSet]
    config_file = "./example_config.json"
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r') as config_file:
            config = json.load(config_file)
    else:
        raise Exception("No config.json found")
    host = f'https://{config["host_address"]}'
    auth = config["auth"]
    wait_time = between(0.500, 0.500)
