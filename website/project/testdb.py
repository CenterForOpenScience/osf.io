from website.models import User, Node

users = User.find()

for user in users:
    print user.fullname