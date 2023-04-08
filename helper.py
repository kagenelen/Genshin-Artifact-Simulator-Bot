import json
import random
import os
import discord

import inventory

def write_file(file, data):
	absolute_path = os.path.dirname(os.path.abspath(__file__)) + "/json_files/"
	with open(absolute_path + file, "w") as f:
		json.dump(data, f, 
					indent=4,  
					separators=(',',': '))

def read_file(file):
	absolute_path = os.path.dirname(os.path.abspath(__file__)) + "/json_files/"
	with open(absolute_path + file, 'rb') as f:
	    data = json.load(f)
	return data

# Select a key based on probability (value), with replacement
# Argument: Dictionary of item and their probability, number to select, needs replacement
# Return: Selected item
def probability_select(data):
	keys = list(data.keys())
	values = list(data.values())
	return random.choices(keys, weights=values, k=1)[0]

# Generate shorthand using first letter of each word
# Argument: Phrase
# Return: Acronym of phrase
def acronym(phrase):
	# Account for special words
	if phrase == "Lavawalker":
		return "LW"
	elif phrase == "Thundersoother":
		return "TS"
	
	words = phrase.split()
	acro = ""
	for word in words:
		acro += word[0]
	return acro

# Parse comma separated string into list
# Argument: comma separated string
# Return: list of string
def parse_into_list(phrase):
	items = phrase.split(",")
	parsed = []
	for item in items:
		parsed.append(item.strip())
	return parsed

# Create list of embed pages, each with max 25 fields
# Argument: Owner's username, user id, filter, List of dictionary for embed field name and value
# Return: List of embeds
def create_embed_page(username, user, filter, artifact_list):
	fodder = "{fodder_num:,}".format(fodder_num = inventory.get_fodder(user))
	description = ("Fodder exp: " + fodder + "\n" + 
				  "Capacity: " + str(inventory.get_capacity(user)) + "/50")

	if filter == None:
		filter = "'s inventory"
	elif filter.lower() == "favourite":
		filter = "'s favourite artifacts"
	elif filter.lower() == "max":
		filter = "'s maxed artifacts"
		
	embed1 = discord.Embed(title="Viewing page 1 of " + username + filter, 
						description=description, 
						color=0xB28CFF)
	embed2 = discord.Embed(title="Viewing page 2 of " + username + "'s' inventory", 
						description=description, 
						color=0xB28CFF)
	embed3 = discord.Embed(title="Viewing page 3 of " + username + "'s' inventory", 
						description=description, 
						color=0xB28CFF)
	embed4 = discord.Embed(title="Viewing page 4 of " + username + "'s' inventory", 
						description=description, 
						color=0xB28CFF)
	embed5 = discord.Embed(title="Viewing page 5 of " + username + "'s' inventory", 
						description=description, 
						color=0xB28CFF)

	# Add artifact to which page depending on number of artifacts in inventory
	for index, arti in enumerate(artifact_list):
		if index < 10:
			embed1.add_field(name=list(arti.keys())[0], value=list(arti.values())[0], inline=False)
		elif index < 20:
			embed2.add_field(name=list(arti.keys())[0], value=list(arti.values())[0], inline=False)
		elif index < 30:
			embed3.add_field(name=list(arti.keys())[0], value=list(arti.values())[0], inline=False)
		elif index < 40:
			embed4.add_field(name=list(arti.keys())[0], value=list(arti.values())[0], inline=False)
		else:
			embed5.add_field(name=list(arti.keys())[0], value=list(arti.values())[0], inline=False)
	
	return [embed1, embed2, embed3, embed4, embed5]

# Check whether requester is owner of artifact
# Argument: artifact object, requester user id
# Return: True if match, False otherwise
# Exception: Invalid artifact id
def is_authorised(id, requester):
	authorised = inventory.get_owner(id)
	if authorised == None:
		return False
	return int(authorised) == int(requester)