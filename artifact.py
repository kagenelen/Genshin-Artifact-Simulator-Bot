import helper
import random
import inventory

MAX_REROLL = 4

class Artifact:
	def __init__(self, id, set, type, level, mainstat, substats, rerolled, sandbox, favourite):
		self.set = set
		self.type = type # 0: Flower, 1: Plume, 2: Sand, 3: Goblet, 4: Circlet
		self.level = level
		self.mainstat = mainstat
		self.substats = substats
		self.rerolled = rerolled
		self.sandbox = sandbox
		self.favourite = favourite

		if id == None:
			data = helper.read_file("config.json")
			self.id = data["artifact_counter"]
			data["artifact_counter"] += 1
			helper.write_file("config.json", data)
		else: 
			self.id = id

	# Create detailed artifact description
	# Argument: None
	# Return: description string
	def display_long(self):
		favourited = ""
		if self.favourite:
			favourited = " 🔒"
			
		description = ("ID " + self.get_id() + favourited + "\n" +
			"Level " + str(self.level * 4) + " "+ self.set + " " + Artifact.readable_type(self.type) + "\n\n" + 
			"Mainstat: \n"
			"　　**" + self.mainstat + "**\n\n" + 
			"Substats: \n")
		for s in self.substats:
			description += "　　" + s + " " + str(self.substats[s]) + "\n"
			
		return description

	# Create short artifact description
	# Argument: None
	# Return: Dictionary. Key is id, level, set, type. Value is stats without number.
	def display_short(self):
		favourited = ""
		if self.favourite:
			favourited = " 🔒"
		
		entry = dict()
		k = "[" + self.get_id() + "] Lvl. " + str(self.level * 4) + " " + helper.acronym(self.set) + " " + Artifact.readable_type(self.type) + favourited
		v = "**" + self.mainstat + "** | "
		for index, s in enumerate(self.substats):
			# Further shorten to EM and ER%
			if s == "Elemental Mastery":
				s = "EM"
			elif s == "Energy Recharge%":
				s = "ER%"
			
			v += s
			if index != len(self.substats) - 1:
				v += ", " # spacing for readability

		entry[k] = v
		return entry

	@staticmethod
	def readable_type(type):
		if type == 0: return "Flower"
		elif type == 1: return "Plume"
		elif type == 2: return "Sand"
		elif type == 3: return "Goblet"
		elif type == 4: return "Circlet"
		
	# Upgrade artifact and update it in inventory
	# Argument: None
	# Return: list[substat, old, new]
	# Exception: Artifact is at level 5 (max), insufficient fodder
	def upgrade(self):
		if self.level >= 5:
			print("Artifact already at max level")
			return None

		# Sandbox artifacts does not require fodder to upgrade
		if not self.sandbox:
			remaining_fodder = upgrade_fodder(self)
			if (remaining_fodder < 0):
				return int(remaining_fodder)
		
		self.level += 1
		substat = ""
		old = 0
		new = 0
		if len(self.substats) < 4:
			# New substat
			substat_prob = helper.read_file("substat_prob.json")
			# Remove mainstat and other substat from prob file
			substat_prob.pop(self.mainstat, None)
			for s in self.substats:
				substat_prob.pop(s, None)
			substat = helper.probability_select(substat_prob)
			value = generate_value(substat, 0)
			self.substats[substat] = value
			old = 0
			new = value

		else:
			# Upgrade existing substat
			keys = list(self.substats.keys())
			substat = random.choices(keys, weights=(1, 1, 1, 1), k=1)[0]
			old = self.substats[substat]
			self.substats[substat] = generate_value(substat, self.substats[substat])
			new = self.substats[substat]

		inventory.update_artifact(self.id, self)
		return [substat, old, new]
		
	def toJSON(self):
		d = dict()
		d["id"] = self.id
		d["set"] = self.set
		d["type"] = self.type
		d["level"] = self.level
		d["mainstat"] = self.mainstat
		d["substats"] = self.substats
		d["rerolled"] = self.rerolled
		d["sandbox"] = self.sandbox
		d["favourite"] = self.favourite
		return d

	@staticmethod
	def fromJSON(dict):
		a = Artifact(dict["id"], dict["set"], dict["type"], dict["level"], dict["mainstat"], dict["substats"], dict["rerolled"], dict["sandbox"], dict["favourite"])
		return a

	# Get artifact image
	# Argument: None
	# Return: URL of image or None if image hasn't been added
	def image(self):
		data = helper.read_file("domain.json")
		type = Artifact.readable_type(self.type).lower()
		for domain in data:
			for set in data[domain]:
				if set["artifact"] == self.set:
					return set["image"].get(type, None)

	# Turn artifact into fodder exp for an user
	# Argument: User id
	# Return: gained fodder exp amount
	def fodder(self, user):
		# Cannot fodder favourite
		if self.favourite:
			return 0
			
		# Foddering sandbox artifacts does not give fodder exp
		fodder = 0
		if not self.sandbox:
			fodder = refund_fodder(user, self, 0.8)
		inventory.delete_inventory_artifact(user, self.id)
		return fodder

	# Toggle artifact's favourite status and update in inventory
	# Argument: None
	# Return: Favourite status (true or false)
	def toggle_favourite(self):
		self.favourite = not self.favourite
		inventory.update_artifact(self.id, self)
		return self.favourite

	# Construct sandbox/reroll id for display purposes
	# Argument: None
	# Return: id string
	def get_id(self):
		if self.rerolled > 0:
			return "R" + str(self.id)
		elif self.sandbox:
			return "S" + str(self.id)
		else:
			return str(self.id)
		
	# Reroll specified substat, reset to level 0 and refund 50% fodder
	# Argument: substat (str) to be rerolled
	# Return: list[substat, value]
	# Exception: Invalid substat, max rerolls reached
	def reroll_substat(self, user, substat):
		substat = stat_alias(substat)
		
		if self.rerolled >= MAX_REROLL:
			return "max"

		if self.substats.pop(substat, None) == None:
			# Invalid substat
			return None

		# Partially refund fodder, reset level and values
		refund_fodder(user, self, -0.5) # TODO change back to 0.5 once currency is implemented
		self.level = 0 
		for s in self.substats:
			self.substats[s] = generate_value(s, 0)
		
		# Generate and replace the specified substat
		new_substat = generate_rerolled_substat(self, substat)
		self.substats[new_substat[0]] = new_substat[1]
		self.rerolled += 1
		inventory.update_artifact(self.id, self)
		return new_substat

		
# Find domain and its artifact sets
# Argument: Domain name
# Return: List of artifact sets
# Exceptions: Domain does not exist
def find_domain(domain):
	domain_data = helper.read_file("domain.json")
	if domain not in domain_data.keys():
		# Domain does not exist
		return None
	else: 
		return domain_data[domain]

# Argument: List of the domain's artifact set
# Return: List of obtained artifacts
def generate_domain_rewards(artifact_sets):
	reward = []

	# Determine 1 or 2 artifact
	artifact_amount = random.choices([1, 2], weights=(94, 6), k=1)[0]
	for i in range(0, artifact_amount):
		set = random.choices(artifact_sets, weights=(1, 1), k=1)[0]
		artifact = generate_artifact(set["artifact"])
		reward.append(artifact)

	return reward

# Makes all domain reward description for discord embed
# Argument: List of obtained artifacts
# Return: Description string
def display_domain_rewards(reward):
	description = ""
	for index, r in enumerate(reward):
		description = description + r.display_long()
		if index != len(reward) - 1:
			description = description + "-----------------------------\n"
	return description
	
# Argument: Set name
# Return: Artifact
def generate_artifact(set):
	# Generate type
	types = [0, 1, 2, 3, 4]
	type = random.choices(types, weights=(1, 1, 1, 1, 1), k=1)[0]

	# Get mainstat
	mainstat = None
	if type == 0:
		mainstat = "HP"
	elif type == 1:
		mainstat = "ATK"
	else:
		mainstat_prob = filter_mainstat(type, helper.read_file("mainstat_prob.json"))
		mainstat = helper.probability_select(mainstat_prob)

	substats = generate_substats(mainstat)

	return Artifact(None, set, type, 0, mainstat, substats, 0, False, False)

# Remove disallowed mainstats based on artifact type
# Argument: Artifact type, probability dictionary
# Return: Probability dictionary
def filter_mainstat(type, prob):
	if type == 2:
		# Sand != dmg bonus, healing, crit
		for k in prob.copy():
			if "Bonus" in k or "CRIT" in k:
				del prob[k]
	elif type == 3:
		# Sand != healing, crit, ER
		for k in prob.copy():
			if "Healing" in k or "CRIT" in k or "Energy" in k:
				del prob[k]
	elif type == 4:
		# Circlet != dmg bonus, ER
		for k in prob.copy():
			if "DMG Bonus" in k or "Energy" in k:
				del prob[k]

	return prob

# Generate 3 or 4 substat and their values
# Argument: Mainstat
# Return: Dictionary of substat and value
def generate_substats(mainstat):
	# Remove mainstat from substat list
	substat_prob = helper.read_file("substat_prob.json")
	substat_prob.pop(mainstat, None)

	# Determine whether to have 3 or 4 substat
	substat_amount = random.choices([3, 4], weights=(1, 1), k=1)[0]
	selected_substats = []
	for i in range(0, substat_amount):
		s = helper.probability_select(substat_prob)
		selected_substats.append(s)
		substat_prob.pop(s, None)

	# Generate each substat's value and add to dictionary
	substats = dict()
	for s in selected_substats:
		substats[s] = generate_value(s, 0)
	
	return substats

# Generate or upgrade substat value
# Argument: Substat type, current value or 0
# Return: New value
def generate_value(substat, curr):
	substat_values = helper.read_file("substat_value.json")
	value = substat_values[substat]
	# Determine percentage of max value
	percentage = random.choices([0.7, 0.8, 0.9, 1], weights=(1, 1, 1, 1), k=1)[0]
	return round(curr + value * percentage, 1)

# Generate rerolled substat
# Argument: artifact object, rerolled substat
# Return: list[substat, value]
def generate_rerolled_substat(arti, reroll):
	# Remove mainstat and current substats from substat list
	substat_prob = helper.read_file("substat_prob.json")
	substat_prob.pop(arti.mainstat, None)
	for s in arti.substats:
		substat_prob.pop(s)
	substat_prob.pop(reroll)

	# Determine the new substat and its value
	selected_substat = helper.probability_select(substat_prob)
	value = generate_value(selected_substat, 0)
	return [selected_substat, value]
	
# Determine how much fodder is needed and deducts it
# Argument: Artifact object
# Return: Remaining fodder
def upgrade_fodder(arti):
	owner = inventory.get_owner(arti.id)
	owner_fodder = inventory.get_fodder(owner)

	required_fodder = 0
	if arti.level == 0:
		required_fodder = 16300
	elif arti.level == 1:
		required_fodder = 28425
	elif arti.level == 2:
		required_fodder = 42425
	elif arti.level == 3:
		required_fodder = 66150
	elif arti.level == 4:
		required_fodder = 117175

	if owner_fodder - required_fodder > 0:
		# Only deduct if there is sufficient fodder
		inventory.add_fodder(owner, -1 * required_fodder)

	# Return will be negative if there is insufficent fodder
	return owner_fodder - required_fodder

# Refund percentage of level as fodder exp
# Argument: user id, artifact object, percentage refund
# Return: amount refunded
def refund_fodder(user, arti, percentage):
	fodder = 0
	if arti.level == 0:
		fodder = 3780 * percentage
	elif arti.level == 1:
		fodder = 16300 * percentage
	elif arti.level == 2:
		fodder = 44725 * percentage
	elif arti.level == 3:
		fodder = 87150 * percentage
	elif arti.level == 4:
		fodder = 153300 * percentage
	elif arti.level == 5:
		fodder = 270475 * percentage
	inventory.add_fodder(user, round(fodder, 0))
	return int(round(fodder, 0))

# Deals with alternative names of stats
# Argument: User input's stat
# Return: Stat string recognised by database
def stat_alias(stat):
	if stat.upper() in ["HP", "DEF", "ATK", "HP%", "DEF%", "ATK%"]:
		return stat.upper()

	stat_low = stat.lower()
	if stat_low in ["em", "elemental mastery"]:
		return "Elemental Mastery"

	if stat_low in ["er%", "er", "energy", "energy recharge", "energy recharge%"]:
		return "Energy Recharge%"

	if stat_low in ["cr%", "cr", "crit rate", "crit rate%"]:
		return "CRIT Rate%"

	if stat_low in ["cd%", "cd", "crit damage", "crit dmg", "crit dmg%"]:
		return "CRIT DMG%"

	if stat_low in ["healing"]:
		return "Healing Bonus%"
		
	if "geo" in stat_low:
		return "Geo DMG Bonus%"

	if "anemo" in stat_low:
		return "Anemo DMG Bonus%"

	if "phys" in stat_low or "physical" in stat_low:
		return "Physical DMG Bonus%"

	if "hydro" in stat_low:
		return "Hydro DMG Bonus%"

	if "pyro" in stat_low:
		return "Pyro DMG Bonus%"

	if "cryo" in stat_low:
		return "Cryo DMG Bonus%"

	if "dendro" in stat_low:
		return "Dendro DMG Bonus%"

	if "electro" in stat_low:
		return "Electro DMG Bonus%"

	return stat

# Deals with alternative names of domains
# Argument: User input's domain
# Return: Domain string recognised by database
def domain_alias(domain):
	d_low = domain.lower()
	if "clear" in d_low or d_low in ["bc", "bloodstained", "bloodstained chivalry", "no", "noblesse", "noblesse oblige"]:
		return "clear pool and mountain cavern"

	if "guyun" in d_low or d_low in ["ap", "archaic", "archaic petra", "rb", "retracing", "bolide", "retracing bolide"]:
		return "domain of guyun"

	if "hidden" in d_low or "zhou" in d_low or d_low in ["cw", "cwof", "crimson", "crimson witch", "crimson witch of flames", "lw", "lavawalker"]:
		return "hidden palace of zhou formula"

	if "midsummer" in d_low or d_low in ["tf", "thundering", "thundering fury", "ts", "thundersoother"]:
		return "midsummer courtyard"

	if "momiji" in d_low or d_low in ["sr", "shimenawa", "shimenawa's reminiscence", "eosf", "emblem", "emblem of severed fate"]:
		return "momiji-dyed court"

	if "peak" in d_low or d_low in ["bs", "blizzard", "hod", "hd", "heart", "heart of depth"]:
		return "peak of vindagnyr"

	if "spire" in d_low or d_low in ["dm", "deepwood", "deepwood memories", "gd", "gilded", "gilded dreams"]:
		return "spire of solitary enlightenment"

	if "valley" in d_low or "remembrance" in d_low or d_low in ["vv", "viridescent", "viridescent venerer", "mb", "maiden", "maiden beloved"]:
		return "valley of remembrance"

	if "gold" in d_low or d_low in ["dpc", "desert", "desert pavilion chronicle", "fopl", "paradise", "flower of paradise lost"]:
		return "city of gold"

	if "slumbering" in d_low or d_low in ["hoop", "husk", "opulent", "husk of opulent dreams", "oc", "clam", "ocean-hued clam"]:
		return "slumbering court"

	if "ridge" in d_low or d_low in ["tenacity", "millelith", "totm", "tenacity of the millelith", "pale", "pf", "pale flame"]:
		return "ridge watch"

	if d_low in ["gladiator", "gf", "wanderer", "wt"]:
		return "boss"

	return domain

# Deals with alternative names of sets
# Argument: User input's set
# Return: Set string recognised by database
def set_alias(set):
	s_low = set.lower().replace('’', '\'')
	domain_data = helper.read_file("domain.json")
	for domain in domain_data:
		# Alias include any word of the set, acronym or full set name
		alias1 = []
		alias2 = []
		alias1.extend(domain_data[domain][0]["artifact"].lower().split())
		alias1.append(helper.acronym(domain_data[domain][0]["artifact"].lower()))
		alias1.append(domain_data[domain][0]["artifact"].lower())
		alias2.extend(domain_data[domain][1]["artifact"].lower().split())
		alias2.append(helper.acronym(domain_data[domain][1]["artifact"].lower()))
		alias2.append(domain_data[domain][1]["artifact"].lower())
		
		if s_low in alias1:
			return domain_data[domain][0]["artifact"]
			
		if s_low in alias2:
			return domain_data[domain][1]["artifact"]
	
	return set

# Create custom artifact
# Argument: set, type, mainstat, 3 or 4 substats in a list
# Return: artifact object
# Exception: Invalid set, type, mainstat, substat or type-mainstat pair
def custom_artifact(a_set, type, mainstat, substats):
	substats = [stat_alias(i) for i in substats if i is not None]
	a_set = set_alias(a_set)
	mainstat = stat_alias(mainstat)
	
	# Check valid set
	valid_set = False
	domain_data = helper.read_file("domain.json")
	for domain in domain_data:
		if domain_data[domain][0]["artifact"] == a_set:
			valid_set = True
		elif domain_data[domain][1]["artifact"] == a_set:
			valid_set = True
			
	if not valid_set:
		return "Invalid set."

	# Check valid type and convert to number
	type = type.lower()
	if type == "flower":
		type = 0
	elif type == "plume":
		type = 1
	elif type == "sand":
		type = 2
	elif type == "goblet":
		type = 3
	elif type == "circlet":
		type = 4
	else:
		return "Invalid type."

	# Check mainstat is valid
	valid_mainstat = False
	mainstat_data = helper.read_file("mainstat_prob.json")
	for m in mainstat_data:
		if m.lower() == mainstat.lower():
			valid_mainstat = True
			mainstat = m
	if mainstat.lower() == "hp" or mainstat.lower() == "atk":
		valid_mainstat = True
		mainstat = mainstat.upper()
	if not valid_mainstat:
		return "Invalid mainstat."

	# Check mainstat matches the type
	valid_pair = True
	if type == 0 and mainstat != "HP":
		valid_pair = False
	elif type == 1 and mainstat != "ATK":
		valid_pair = False
	elif type == 2 and ("Bonus" in mainstat or "CRIT" in mainstat):
		valid_pair = False
	elif type == 3 and ("Healing" in mainstat or "CRIT" in mainstat):
		valid_pair = False
	elif type == 4 and ("DMG Bonus" in mainstat or "Energy" in mainstat):
		valid_pair = False
	if not valid_pair:
		return "Mainstat and types does not match."
	
	# Check valid substat
	valid_substat = False
	substat_data = helper.read_file("substat_prob.json")
	for custom_s in substats:
		for s in substat_data:
			if s.lower() == custom_s.lower():
				valid_substat = True
				custom_s = s
		if not valid_substat:
			return "Invalid substat."
		valid_substat = False

	# Generate value for substats
	substat_values = dict()
	for s in substats:
		substat_values[s] = generate_value(s, 0)

	# Check if any of the substat and mainstat is the same
	substats.append(mainstat)
	duplicate = set(substats)
	if len(duplicate) != len(substats):
		return "Cannot have duplicate mainstat or substat."
	
	# Create artifact
	return Artifact(None, a_set, type, 0, mainstat, substat_values, 0, True, False)