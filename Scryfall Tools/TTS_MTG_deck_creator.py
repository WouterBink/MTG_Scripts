'''Creates the files needed for a Magic: The Gathering deck
used in TableTop Simulator
'''

import scryfall_tools
from scryfall_tools import card_sizes
import dropbox_uploader
import json
import time
from datetime import datetime
import sys
from io import BytesIO
from PIL import Image
from pathlib import Path
from random import randint

# Cardback and ad cards taken from https://deckmaster.info,
# backed up to dropbox for persistency and loading issues
back_1_url = "https://www.dropbox.com/s/9aecuelfwga8bv4/back_1.jpg?dl=1"
back_2_url = "https://www.dropbox.com/s/ral1ldk9odsycqd/back_2.jpg?dl=1"

ad_urls = [
    "https://www.dropbox.com/s/jbnpcn4xs14myot/token_1.jpg?dl=1",
    "https://www.dropbox.com/s/7lvnf1z6paj6ds9/token_2.jpg?dl=1",
    "https://www.dropbox.com/s/pb4um3zm56i2nuj/token_3.jpg?dl=1",
    "https://www.dropbox.com/s/xx14lh7qty4x9a2/token_4.jpg?dl=1",
    "https://www.dropbox.com/s/p512mi23b3ptb4h/token_5.jpg?dl=1",
    "https://www.dropbox.com/s/w0ro7596gp5kk05/token_6.jpg?dl=1",
    "https://www.dropbox.com/s/dobryp84n34tjha/token_7.jpg?dl=1",
    "https://www.dropbox.com/s/a5sahr1jmuk51h8/token_8.jpg?dl=1",
    "https://www.dropbox.com/s/ss0pch8fdnv3f5i/token_9.jpg?dl=1",
    "https://www.dropbox.com/s/tw03iokf84smj74/token_10.jpg?dl=1",
    "https://www.dropbox.com/s/xk4bo87zp4aoq59/token_11.jpg?dl=1",
    "https://www.dropbox.com/s/ckvcduv45ha9e3x/token_12.jpg?dl=1"
]


def get_contained_object(nickname, card_id):
    transform = {
        "posX": 0.0, "posY": 0.0, "posZ": 0.0,
        "rotX": 0.0, "rotY": 180, "rotZ": 180,
        "scaleX": 1, "scaleY": 1, "scaleZ": 1
    }

    return {
        "Name": "Card",
        "Nickname": nickname,
        "Transform": transform,
        "CardID": card_id
    }


sf_unique_cards = {}
sf_card_ids = {}

df_unique_cards = {}
df_card_ids = {}


def collect_ids(deck):
    deck_as_ids = {}
    for card in deck:
        if card['layout'] in ('transform', 'double_faced_token'):
            if card['id'] not in df_card_ids:
                card_id = (int(len(df_card_ids) / 24) * 100 +
                           len(df_card_ids) % 24 + 100)
                df_card_ids[card['id']] = card_id
                df_unique_cards[card_id] = card
            else:
                card_id = df_card_ids[card['id']]
        else:
            if card['id'] not in sf_card_ids:
                card_id = (int(len(sf_card_ids) / 24) * 100 +
                           len(sf_card_ids) % 24 + 100)
                sf_card_ids[card['id']] = card_id
                sf_unique_cards[card_id] = card
            else:
                card_id = sf_card_ids[card['id']]

        if card_id not in deck_as_ids:
            deck_as_ids[card_id] = 1
        else:
            deck_as_ids[card_id] += 1

    return deck_as_ids


def transform_decks(decks):
    tokens = []
    dfcs = []
    for deck in decks:
        deck_tokens = []
        deck_dfcs = []
        for card in deck:
            if 'all_parts' in card:
                for related_entry in card['all_parts']:
                    if (related_entry['component'] == 'token' or
                            related_entry['component'] == 'combo_piece' and
                            'Emblem' in related_entry['name']):
                        token = scryfall_tools.get_card(
                            '',
                            uri=related_entry['uri']
                        )
                        if token not in deck_tokens:
                            deck_tokens.append(token)
                    if related_entry['component'] == 'meld_result':
                        meld_result = scryfall_tools.get_card(
                            '',
                            uri=related_entry['uri']
                        )
                        if meld_result not in deck_tokens:
                            deck_tokens.append(meld_result)
            if card['layout'] == 'transform':
                deck_dfcs.append(card)

        for card in deck_dfcs:
            deck.remove(card)
        tokens.append(deck_tokens)
        dfcs.append(deck_dfcs)

    main_decks_as_ids = [collect_ids(deck) for deck in decks]
    token_decks_as_ids = [collect_ids(deck) for deck in tokens]
    dfc_decks_as_ids = [collect_ids(deck) for deck in dfcs]

    return main_decks_as_ids, token_decks_as_ids, dfc_decks_as_ids


def create_deck_image_containers(card_size):
    # The initial images for the deck
    sf_images = []
    image_pages = int((len(sf_card_ids)) / 24)
    image_rest = (len(sf_card_ids)) % 24
    for _ in range(image_pages):
        sf_images.append((Image.new('RGB',
                                    [i * 5 for i in card_size])))
    if image_rest > 0:
        rows = int((image_rest) / 5) + 1
        sf_images.append(Image.new('RGB',
                                   [card_size[0] * 5, card_size[1] * rows]))

    # Pages for DFCs
    dfc_images = []
    dfc_pages = int(len(df_card_ids) / 24) * 2
    dfc_rest = len(df_card_ids) % 24
    for _ in range(dfc_pages):
        dfc_images.append((Image.new('RGB', [i * 5 for i in card_size])))
    if dfc_rest > 0:
        rows = int((dfc_rest + 1) / 5) + 1
        dfc_images.append(Image.new(
            'RGB', [card_size[0] * 5, card_size[1] * rows]
        ))
        dfc_images.append((Image.new(
            'RGB', [card_size[0] * 5, card_size[1] * rows]
        )))

    return sf_images, dfc_images


def create_deck_images(card_size_text):
    print("Creating base images...")
    card_size = card_sizes[card_size_text]
    sf_images, df_images = create_deck_image_containers(card_size)

    start = time.time()
    for card_id, card in sf_unique_cards.items():
        # Get the basic information for drawing the image
        image_page = int((card_id - 100) / 100)
        image_on_page = (card_id - 100 * (image_page + 1)) % 24
        image_box = (card_size[0] * (image_on_page % 5),
                     card_size[1] * int(image_on_page / 5))
        print(f'Handling {card["name"]} - {card_id}...\t\t\t\t\t', end='\r')

        front_uri = card['image_uris'][card_size_text]

        # Make sure to leave 100 ms between Scryfall calls
        between = time.time() - start
        if between < 0.1:
            time.sleep(0.1 - between)
        start = time.time()
        card_image = scryfall_tools.get_card_image(uri=front_uri)
        sf_images[image_page].paste(Image.open(BytesIO(card_image)),
                                    box=image_box)
    print()

    for card_id, card in df_unique_cards.items():
        print(f'Handling {card["name"]} - {card_id}...\t\t\t\t\t', end='\r')
        image_page = int((card_id - 100) / 100)
        image_on_page = (card_id - 100 * (image_page + 1)) % 24
        image_box = (card_size[0] * (image_on_page % 5),
                     card_size[1] * int(image_on_page / 5))

        if card['layout'] == 'meld':
            front_uri = card['image_uris'][card_size_text]
            back_uri = card['image_uris'][card_size_text]
        if card['layout'] == 'transform':
            front_uri = card['card_faces'][0]['image_uris'][card_size_text]
            back_uri = card['card_faces'][1]['image_uris'][card_size_text]

        # Make sure to leave 100 ms between Scryfall calls
        # TODO: query multiple cards together
        between = time.time() - start
        if between < (0.1 * 2):
            time.sleep((0.1 * 2) - between)
        start = time.time()
        card_image_front = scryfall_tools.get_card_image(uri=front_uri)
        card_image_back = scryfall_tools.get_card_image(uri=back_uri)

        df_images[image_page * 2].paste(
            Image.open(BytesIO(card_image_front)),
            box=image_box
        )
        df_images[image_page * 2 + 1].paste(
            Image.open(BytesIO(card_image_back)),
            box=image_box
        )

    print("Saving images...")
    sf_urls = save_deck_images(sf_images)
    df_urls = save_deck_images(df_images)

    return sf_urls, df_urls


def save_deck_images(images):
    urls = []
    for i, image in enumerate(images):
        image_bytes = BytesIO()
        image.save(image_bytes, format='png')
        dropbox_url = dropbox_uploader.upload_to_dropbox(
            image_bytes.getvalue(),
            f'TTS_{datetime.now():%Y-%m-%d-%H_%M_%S}.png'
        )
        if not dropbox_url:
            return []
        urls.append(dropbox_url)

    return urls


def create_deck_jsons(decks, sf_urls, df_urls, path, name):
    # The base JSON container
    base = {}
    base['ObjectStates'] = []

    sf_pages = int((len(sf_card_ids)) / 24)
    last_rows = int((len(sf_card_ids) % 24) / 5) + 1
    last_columns = 5 if last_rows > 1 else (len(sf_card_ids) % 24) % 5

    back_url = back_1_url if randint(0, 1000) < 1000 else back_2_url
    main_customdeck = {
        i + 1: {
            "NumWidth": 5,
            "NumHeight": 5 if i < sf_pages else last_rows,
            "FaceURL": url,
            "BackURL": back_url
        }
        for i, url in enumerate(sf_urls)
        # Ignore the page if it contains only tokens
        if not sf_unique_cards[(i + 1) * 100]['layout'] == 'token'
    }

    token_customdeck = {
        i + 1: {
            "NumWidth": 5,
            "NumHeight": 5 if i < sf_pages else last_rows,
            "FaceURL": url,
            "BackURL": ad_urls[randint(0, len(ad_urls) - 1)]
        }
        for i, url in enumerate(sf_urls)
        # Ignore the page if it doesn't contain tokens
        if sf_unique_cards[
            (i + 1) * 100 +  # Base count (left-topmost card)
            (23 if i < sf_pages else  # right-bottommost card for a full page
             (last_rows - 1) * 5 + (len(sf_card_ids) % 24) % 5 - 1)
        ]['layout'] in ['token', 'emblem', 'meld']
    }

    df_pages = int((len(df_card_ids)) / 24) + 1
    last_rows = int((len(df_card_ids) % 24) / 5) + 1
    last_columns = 5 if last_rows > 1 else (len(df_card_ids) % 24) % 5
    df_customdeck = {
        i + 1: {
            "NumWidth": 5,
            "NumHeight": 5 if i + 1 < df_pages else last_rows,
            "UniqueBack": True,
            "FaceURL": df_urls[i * 2],
            "BackURL": df_urls[i * 2 + 1]
        }
        for i in range(int(len(df_urls) / 2))
    }

    # Add the df-fronts to the main deck
    for i, df_url in enumerate(df_urls):
        if not i % 2 == 0:
            continue
        main_customdeck[len(main_customdeck) + 1] = {
            "NumWidth": 5,
            "NumHeight": 5 if i + 1 < df_pages else last_rows,
            "FaceURL": df_url,
            "BackURL": back_url
        }

    for i, (deck_name, deck, tokens, dfcs) in enumerate(decks):
        # The main deck
        if deck:
            deck_container = {}
            deck_container['Transform'] = {
                "posX": i * 3, "posY": 1.0, "posZ": -0.0,
                "rotX": 0, "rotY": 180, "rotZ": 180,
                "scaleX": 1, "scaleY": 1, "scaleZ": 1
            }
            deck_container['Name'] = 'DeckCustom'
            deck_container['Nickname'] = f'{deck_name}'
            deck_container['CustomDeck'] = main_customdeck
            deck_container['ContainedObjects'] = [
                get_contained_object(sf_unique_cards[card_id]['name'], card_id)
                for card_id, amount in deck.items() for i in range(amount)
            ]
            deck_container['DeckIDs'] = [
                card_id for card_id, amount in deck.items() for i in range(amount)
            ]

            df_offset = 100 * (int(len(deck) / 24) + 1)
            deck_container['ContainedObjects'] += [
                get_contained_object(df_unique_cards[card_id]['name'], card_id + df_offset)
                for card_id, amount in dfcs.items() for i in range(amount)
            ]
            deck_container['DeckIDs'] += [
                card_id + df_offset for card_id, amount in dfcs.items() for i in range(amount)
            ]

            base['ObjectStates'] += [deck_container]

        # The token container
        if tokens:
            token_deck = {}
            token_deck['Transform'] = {
                "posX": i * 3, "posY": 1.0, "posZ": 4.0,
                "rotX": 0, "rotY": 180, "rotZ": 0,
                "scaleX": 1, "scaleY": 1, "scaleZ": 1
            }
            token_deck['Name'] = 'DeckCustom'
            token_deck['Nickname'] = f'{deck_name} [tokens]'
            token_deck['CustomDeck'] = token_customdeck
            token_deck['ContainedObjects'] = [
                get_contained_object(sf_unique_cards[card_id]['name'], card_id)
                for card_id, amount in tokens.items() for i in range(amount)
            ]
            token_deck['DeckIDs'] = [
                card_id for card_id, amount in tokens.items() for i in range(amount)
            ]
            base['ObjectStates'] += [token_deck]

        # The DFC container
        if dfcs:
            dfc_deck = {}
            dfc_deck['Transform'] = {
                "posX": i * 3, "posY": 1.0, "posZ": 8.0,
                "rotX": 0, "rotY": 180, "rotZ": 0,
                "scaleX": 1, "scaleY": 1, "scaleZ": 1
            }
            if len(dfcs) == 1:
                dfc = list(dfcs.keys())[0]
                dfc_deck['Name'] = 'Card'
                dfc_deck['Nickname'] = df_unique_cards[dfc]['name']
                dfc_deck['CardID'] = 100
                dfc_deck['CustomDeck'] = df_customdeck
            else:
                dfc_deck['Name'] = 'DeckCustom'
                dfc_deck['Nickname'] = f'{deck_name} [dfc]'
                dfc_deck['CustomDeck'] = df_customdeck
                dfc_deck['ContainedObjects'] = [
                    get_contained_object(df_unique_cards[card_id]['name'], card_id)
                    for card_id, amount in dfcs.items() for i in range(amount)
                ]
                dfc_deck['DeckIDs'] = [
                    card_id for card_id, amount in dfcs.items() for i in range(amount)
                ]

            base['ObjectStates'] += [dfc_deck]

    json_path = Path(path or Path().absolute(),
                     f'{name}.json')
    with open(json_path, 'w') as outfile:
        json.dump(base, outfile, indent=2, ensure_ascii=False)


def create_TTS_MTG_decks(decks, path='',
                         card_size_text="normal"):
    print("Gathering unique cards...")
    mains_as_ids, tokens_as_ids, dfcs_as_ids = transform_decks(decks.values())

    print("Creating deck images...")
    sf_urls, df_urls = create_deck_images(card_size_text)

    if not sf_urls and not df_urls:
        print("Something went wrong with uploading the deck images.")
        return

    create_deck_jsons(
        zip([deck for deck in decks],
            mains_as_ids,
            tokens_as_ids,
            dfcs_as_ids),
        sf_urls, df_urls, path, list(decks.keys())[0]
    )

    return
