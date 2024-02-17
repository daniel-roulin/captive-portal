import json

def save_credentials(username, password):
    with open('credentials/credentials.json', "r") as f:
        credentials = json.load(f)

    credentials[username] = password

    with open('credentials/credentials.json', "w") as f:
        json.dump(credentials, f, sort_keys=True, indent=4, separators=(',', ': '))