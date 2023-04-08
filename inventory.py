import helper
import artifact

INITIAL_FODDER = 1500000

# Save an artifact to an user's inventory
# Argument: user discord id, artifact
# Return: None
def save_inventory_artifact(user, arti):
	user = str(user)
	arti = arti.toJSON()
	data = helper.read_file("inventory.json")
	inventory = data.get(user, None)
	if inventory == None:
		# Create inventory for new user
		data[user] = {
			"fodder": INITIAL_FODDER,
			"artifact": [arti]
		}
	else:
		data[user]["artifact"].append(arti)
	helper.write_file("inventory.json", data)

# Delete artifact from user's inventory
# Argument: user id, artifact id
# Return: None
# Exception: User does not have an inventory
def delete_inventory_artifact(user, id):
	user = str(user)
	data = helper.read_file("inventory.json")
	inventory = data.get(user, None)
	if inventory == None:
		return

	for item in inventory["artifact"].copy():
		if item["id"] == id:
			inventory["artifact"].remove(item)
	helper.write_file("inventory.json", data)

# Read user's artifact inventory
# Argument: user discord id
# Return: list of artifacts
def read_inventory_artifact(user):
	user = str(user)
	data = helper.read_file("inventory.json")
	inventory = data.get(user, None)
	if inventory == None:
		# Create inventory for new user
		data[user] = {
			"fodder": INITIAL_FODDER,
			"artifact": []
		}
		helper.write_file("inventory.json", data)
		
	# Convert json to artifact objects
	artifact_list = []
	for r in data[user]["artifact"]:
		artifact_list.append(artifact.Artifact.fromJSON(r))
	return artifact_list

# Find artifact by id (all user)
# Argument: artifact id
# Return: artifact or none if not found
def find_artifact(id):
	data = helper.read_file("inventory.json")
	if isinstance(id, str):
		id = id.strip("srSR")
		id = int(id)
	
	for user in data:
		for arti in data[user]["artifact"]:
			if arti["id"] == id:
				return artifact.Artifact.fromJSON(arti)
	return None

# Update specified artifact with another artifact in inventory
# Argument: artifact id, new artifact
# Return: None
def update_artifact(id, arti):
	id = int(id)
	data = helper.read_file("inventory.json")
	for user in data:
		for index, a in enumerate(data[user]["artifact"]):
			if a["id"] == id:
				# Replace this artifact entry
				a = arti.toJSON()
				data[user]["artifact"][index] = a
				helper.write_file("inventory.json", data)

# Create strings of all artifacts for embed fields to display inventory
# Argument: User id, type of filter (max/favourite/sandbox/reroll)
# Return: List of dictionary. Key is the field name, and value is field value
def display_inventory(user, filter):
	artifact_list = read_inventory_artifact(user)
	inventory = []
	for a in artifact_list:
		if filter == None:
			inventory.append(a.display_short())
		elif filter.lower() == "lock" and a.favourite == True:
			inventory.append(a.display_short())
		elif filter.lower() == "max" and a.level == 5:
			inventory.append(a.display_short())
		elif filter.lower() == "sandbox" and a.sandbox:
			inventory.append(a.display_short())
		elif filter.lower() == "reroll" and a.rerolled > 0:
			inventory.append(a.display_short())
		elif filter.lower() == "unmax" and a.level != 5:
			inventory.append(a.display_short())
		elif filter.lower() == "unlock" and a.favourite == False:
			inventory.append(a.display_short())
		
	return inventory

# Determine user's fodder exp
# Argument: User id
# Return: Amount of fodder exp
def get_fodder(user):
	user = str(user)
	data = helper.read_file("inventory.json")
	inventory = data.get(user, None)
	if inventory == None:
		# Create inventory for new user
		data[user] = {
			"fodder": INITIAL_FODDER,
			"artifact": []
		}
		helper.write_file("inventory.json", data)
	return data[user]["fodder"]

# Add specified fodder to user's current fodder amount
# Argument: User id, new fodder exp
# Return: None
def add_fodder(user, fodder):
	user = str(user)
	data = helper.read_file("inventory.json")
	inventory = data.get(user, None)
	if inventory == None:
		# Create inventory for new user
		data[user] = {
			"fodder": INITIAL_FODDER,
			"artifact": []
		}
	data[user]["fodder"] = int(round(data[user]["fodder"] + fodder, 0))
	helper.write_file("inventory.json", data)

# Fodder all unlocked artifacts of a user
# Argument: User id
# Return: Fodder earnt
def fodder_all(user):
	user = str(user)
	artifact_list = read_inventory_artifact(user)
	
	fodder_amount = 0
	for arti in artifact_list:
		arti_fodder = arti.fodder(user)
		fodder_amount += arti_fodder
	return fodder_amount
	
# Determine how much artifacts an user has in their inventory
# Argument: User id
# Return: Amount of artifacts
def get_capacity(user):
	return len(read_inventory_artifact(user))

# Get the discord id of the artifact's owner
# Argument: Artifact id
# Return: Owner's discord id
# Exception: Invalid artifact id
def get_owner(id):
	data = helper.read_file("inventory.json")
	if isinstance(id, str):
		id = id.strip("srSR")
		id = int(id)
	
	for user in data:
		for arti in data[user]["artifact"]:
			if arti["id"] == id:
				return int(user)
	return None