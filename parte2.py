import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from urllib.parse import urlencode, quote
import json
import sqlite3

# Define headers for HTTP requests to mimic a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
}

# Wikipedia URL containing a list of Generation I Pokémon
url = 'https://en.wikipedia.org/wiki/List_of_generation_I_Pok%C3%A9mon'

# Pokémon TCG API endpoint
apiEndpoint = "https://api.pokemontcg.io/v2"

# Send an HTTP GET request to the Wikipedia page
page = requests.get(url, headers=headers)

# Connect to a SQLite database (or create it if it doesn't exist)
db_conn = sqlite3.connect('question1.db')
cursor = db_conn.cursor()

# Parse the HTML content of the Wikipedia page using BeautifulSoup
soup = BeautifulSoup(page.content, "html.parser")

# API key for the Pokémon TCG API
apiKey = "9d28cada-6ac5-4ea6-a897-e4517188e29d"

# Initialize lists to store Pokémon data
names = []         # Pokémon names
types = []         # Pokémon types
evolvedFrom = []   # Pokémon evolution origins
notes = []         # Additional notes
cardAmmounts = []  # Number of cards for each Pokémon
hpList = []        # Maximum HP of cards for each Pokémon
atkList = []       # Maximum attack power of cards for each Pokémon

# Iterate over each row in the Pokémon table on the Wikipedia page
for row in soup.select("tbody > tr"):
    # Check if the row has an "id" attribute (indicating a Pokémon entry)
    if row.has_attr("id"):
        id = row["id"]  # Get the Pokémon's ID (name)
        names.append(row["id"])  # Add the name to the list

        # Prepare query parameters for the Pokémon TCG API
        params = {
            # Remove gender symbols
            "q": f"name:{id.removesuffix('♀').removesuffix('♂')}",
            "select": "name,id,hp,attacks,supertype"  # Select specific fields
        }

        # Encode the query parameters
        encoded_params = urlencode(params)

        # Send a GET request to the Pokémon TCG API
        response = requests.get(
            f"{apiEndpoint}/cards?{encoded_params}", headers={"X-Api-Key": apiKey})

        # Parse the API response as JSON
        response_dict = response.json()

        # Save the API response to a JSON file for debugging
        with open("api_response.json", "w", encoding="utf-8") as json_file:
            json.dump(response_dict, json_file, ensure_ascii=False, indent=4)

        # Extract the number of cards and initialize variables for max HP and attack
        cardAmmount = response_dict["count"]
        maxHP = 0
        maxAtk = 0

        # Iterate over each card in the API response
        for card in response_dict["data"]:
            # Skip cards that are not of type "Pokémon"
            if card["supertype"] != "Pokémon":
                continue
            else:
                # Update max HP if the card's HP is higher
                if int(card["hp"]) > maxHP:
                    maxHP = int(card["hp"])

                # Check for attack damage and update max attack if applicable
                if card.get("damage"):
                    for atk in card["attacks"]:
                        if atk.get("damage") and atk["damage"] != "":
                            dmg = atk["damage"].removesuffix(
                                "×").removesuffix("+").removesuffix('-')
                            if int(dmg) > maxAtk:
                                maxAtk = int(dmg)

        # Append the extracted data to the respective lists
        cardAmmounts.append(cardAmmount)
        hpList.append(maxHP)
        atkList.append(maxAtk)

        # Extract additional data from the Wikipedia table
        if row.select("td:nth-child(3)") != []:
            el = soup.find(id=id)  # Find the row by ID
            type = el.select_one("td:nth-child(3)")  # Pokémon type
            eFrom = el.select_one("td:nth-child(4)")  # Evolution origin
            note = ""

            # Handle notes based on evolution status
            if "No evolution" in eFrom.get_text():
                note = el.select_one("td:nth-child(5)")
            else:
                note = el.select_one("td:nth-child(6)")

            # Append the extracted data to the respective lists
            notes.append(note.get_text())
            cleaned_text = re.sub(
                r'\s*\[.*?\]$', '', type.get_text()).removesuffix("\n")
            types.append(cleaned_text)
            evolvedFrom.append(eFrom.get_text().removesuffix(
                "\n").replace("—", "N/A"))

# Create dictionaries for the extracted data
data1 = {"Names": names, "Type(s)": types,
         "Evolved From": evolvedFrom, "Notes": notes}
data2 = {"Ammount of Cards": cardAmmounts,
         "Highest HP": hpList, "Highest Attack Power": atkList}

# Create Pandas DataFrames from the dictionaries
df1 = pd.DataFrame(data=data1, dtype=str)
df2 = pd.DataFrame(data=data2, dtype=int)

# Concatenate the two DataFrames into a single DataFrame
df3 = pd.concat([df1, df2], axis=1)

# Print the final DataFrame
print(df3)

# Save the DataFrame to a SQLite database table
df3.to_sql('pkmn', db_conn, if_exists='replace', index=False)

# Save the DataFrame to a CSV file
df3.to_csv('output.csv', index=False)
