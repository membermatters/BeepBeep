import config

# webrepl only allows passwords up to 9 characters
PASS = config.API_SECRET[:9]
