import json
import os
from locust import HttpUser, task, between

from appian_locust import AppianTaskSet

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


class GetFrontPageTaskSet(AppianTaskSet):
    @task
    def get_front_page(self):
        self.client.get('/suite/tempo')


class GetAdminPageTaskSet(AppianTaskSet):
    @task
    def get_admin_page(self):
        self.client.get('/suite/admin')


def get_config(file_name):
    config_file = os.path.join(CURRENT_DIR, file_name)
    if os.path.exists(config_file):
        with open(config_file, 'r') as config_file:
            return json.load(config_file)
    else:
        raise Exception("No config.json found")


class FrontendUserActor(HttpUser):
    """
    This represents the user that will interact with the frontend
    It uses the corresponding taskset that hits the basic tempo page

    The weight parameter here means for every 4 users spun up, 3 will be a frontend user

    The wait_time parameter is how long between tasks each simulated user will wait (half a second)
    """
    tasks = [GetFrontPageTaskSet]
    config = get_config('example_config.json')
    host = f'https://{config["host_address"]}'
    auth = config["auth"]
    wait_time = between(0.500, 0.500)
    weight = 3

class AdminUserActor(HttpUser):
    """
    This represents the user that will interact with the admin panel
    It uses the corresponding taskset that hits the admin landing page and the config for the admin user (i.e. admin creds)

    The weight parameter here means for every 4 users spun up, 1 will be an admin user

    The wait_time parameter is how long between tasks each simulated user will wait (one second)
    """
    tasks = [GetAdminPageTaskSet]
    config = get_config('example_admin_config.json')
    host = f'https://{config["host_address"]}'
    auth = config["auth"]
    wait_time = between(1.000, 1.000)
    weight = 1
