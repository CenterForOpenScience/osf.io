import yaml
from website import settings

with open(settings.WAFFLE_VALUES_YAML) as stream:
    features = yaml.safe_load(stream)

for flag in features['flags']:
    locals()[flag.pop('flag_name')] = flag['name']

for switch in features['switches']:
    locals()[switch.pop('flag_name')] = switch['name']
