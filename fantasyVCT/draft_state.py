import queue
import random

class DraftState:

	def __init__(self):
		self.draft_started = False
		self.draft_complete = False
		self.registered_users = list()
		self.queue = queue.Queue()
		self.current_drafter = None
		self.num_rounds = 7

	def is_draft_complete(self):
		return self.draft_complete

	def is_draft_started(self):
		return self.draft_started

	def start_draft(self, registered_users):
		# randomize user order
		self.registered_users = registered_users
		random.shuffle(self.registered_users)
		# put users in queue for snake draft
		for i in range(self.num_rounds):
			self.registered_users.reverse()
			for user_id in self.registered_users:
				self.queue.put(user_id)
		self.draft_started = True
		self.current_drafter = self.queue.get()
		return self.current_drafter

	def can_draft(self, user_id):
		if self.draft_complete:
			return True
		elif self.draft_started:
			if str(user_id) == str(self.current_drafter):
				return True
		return False

	def next(self):
		if self.queue.empty():
			self.draft_complete = True
			return None
		self.current_drafter = self.queue.get()
		return self.current_drafter

	def skip_draft(self):
		self.draft_started = True
		self.draft_complete = True

	def set_num_rounds(self, num_rounds: int):
		self.num_rounds = num_rounds
