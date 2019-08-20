from .api import ApiService


class SyncEnvRegistration:

    def register(self):
        api_service = ApiService()
        client_env_name = ''
        while not client_env_name:
            client_env_name = input('Descriptor of the environment: ').strip()
        response = api_service.add_client_env(client_env_name)
        print(f"Registered environment '{client_env_name}' for your user.")
