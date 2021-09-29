import queue
import random

class Status:

	def __init__(self):
		self.draft_started = False
		self.draft_complete = False
		self.registered_users = list()
		self.queue = queue.Queue()

	def is_draft_complete(self):
		return self.draft_complete

	def is_draft_started(self):
		return self.draft_started

	def register_user(self, user_id):
		if self.draft_started or self.draft_complete:
			return False
		else:
			self.registered_users.append(user_id)
			return True

	def start_draft(self):
		# randomize user order
		random.shuffle(self.registered_users)
		# put users in queue for snake draft
		for i in range(10):
			self.registered_users.reverse()
			for user_id in self.registered_users:
				self.queue.put(user_id)
		self.draft_started = True

	def can_draft(self, user_id):
		if self.draft_complete:
			return True
		elif self.draft_started:
			if user_id is self.queue[0]:
				return True
		return False

	def next(self):
		if self.queue.empty():
			self.draft_complete = True
			return None
		return self.queue.get()
