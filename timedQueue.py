import discord
from discord.ext import tasks, commands


class QueueUser:
    def __init__(self, name, queue):
        self.name = name
        self.queue = queue

    def __eq__(self, other):
        return self.member == other.member


class TimedQueue:
    FULL = 2
    NOTFULL = 1
    EMPTY = 0

    user_lifetime_minutes = 30

    def __init__(self, originator: QueueUser, queue_name: str, min_req: int):
        self.user_time_list = {}
        self.name = queue_name

        if min_req >= 4:
            self.min_req = int(min_req / 2)
        else:
            self.min_req = min_req

        self.manage_users.start()

    def append(self, queue_user: QueueUser):
        self.user_time_list[queue_user] = self.user_lifetime_minutes

    def add_user(self, name):
        self.user_lifetime_minutes[QueueUser(
            name, self)] = self.user_lifetime_minutes

    def remove(self, queue_user: QueueUser):
        self.user_time_list.pop(queue_user, None)

    def status(self):
        if len(self.userlist) == 0:
            return IndividQueue.EMPTY
        elif len(self.userlist) < self.min_req:
            return IndividQueue.NOTFULL
        elif len(self.userlist) == self.min_req:
            return IndividQueue.FULL

    def __len__(self):
        return len(self.userlist)

    def __eq__(self, other):
        return self.name == other.name

    @tasks.loop(minutes=1.0)
    async def manage_users(self):
        for user in self.user_time_list:
            if self.user_time_list[user] <= 0:
                self.user_time_list.pop(user, None)
            else:
                self.user_time_list[user] -= 1
