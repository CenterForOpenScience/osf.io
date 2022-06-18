import yaml

with open('osf/features.yaml', 'r') as stream:
    features = yaml.safe_load(stream)

for flag in features['flags']:
    locals()[flag.pop('flag_name')] = flag['name']

for switch in features['switches']:
    locals()[switch.pop('flag_name')] = switch['name']
