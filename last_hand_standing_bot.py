import logging
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

# =========================
# Logging
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# =========================
# Card Catalog
# =========================
# Fields per card:
# - name: shown to players
# - rarity: "starter" | "common" | "uncommon" | "curse"
# - cost: 0, 1, 2, "X", or None for unplayable
# - target: "self", "other", "any", "multi_other", "multi_any", "none"
# - description: rules text (engine is a simplified subset)

CARD_CATALOG: Dict[str, Dict] = {
    # ===== CURSE (generic, used by many effects) =====
    "CURSE": {
        "name": "Curse",
        "rarity": "curse",
        "cost": None,
        "target": "none",
        "description": "Unplayable. Does nothing except take up space in your hand.",
    },

    # ===== STARTER DECK =====
    "BASE_VOTE": {
        "name": "Base Vote",
        "rarity": "starter",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote.",
    },
    "BLOCK_1": {
        "name": "Block 1",
        "rarity": "starter",
        "cost": 1,
        "target": "self",
        "description": "Block 1 vote against you.",
    },
    "ASSIST_ALLY": {
        "name": "Assist Ally",
        "rarity": "starter",
        "cost": 1,
        "target": "other",
        "description": "Give 1 extra vote to another player. They secretly choose who receives that vote.",
    },
    "BLOCK_ALLY": {
        "name": "Block Ally",
        "rarity": "starter",
        "cost": 1,
        "target": "other",
        "description": "Give 1 block to another player.",
    },
    "PEEK": {
        "name": "Peek",
        "rarity": "starter",
        "cost": 1,
        "target": "other",
        "description": "Secretly look at another player’s hand.",
    },
    "SURVIVE": {
        "name": "Survive",
        "rarity": "starter",
        "cost": 1,
        "target": "self",
        "description": "Gain 2 blocks. Discard 1 card.",
    },
    "WEAKEN": {
        "name": "Weaken",
        "rarity": "starter",
        "cost": 1,
        "target": "other",
        "description": "Cancel 1 random card from target player.",
    },

    # ===== COMMONS =====
    "PLUS_ONE_VOTE": {
        "name": "+1 Vote",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote.",
    },
    "SHIELD": {
        "name": "Shield",
        "rarity": "common",
        "cost": 1,
        "target": "self",
        "description": "Block 1 vote.",
    },
    "QUICK_DRAW": {
        "name": "Quick Draw",
        "rarity": "common",
        "cost": 1,
        "target": "none",
        "description": "Draw 2 cards.",
    },
    "ENERGY_SURGE": {
        "name": "Energy Surge",
        "rarity": "common",
        "cost": 1,
        "target": "self",
        "description": "Gain +2 Energy this round.",
    },
    "PRESSURE_VOTE": {
        "name": "Pressure Vote",
        "rarity": "common",
        "cost": 0,
        "target": "other",
        "description": "Cast 1 vote that must be revealed publicly.",
    },
    "GROUP_TALK": {
        "name": "Group Talk",
        "rarity": "common",
        "cost": 1,
        "target": "none",
        "description": "Reveal all cards you played this round to group; gain +1 card next round.",
    },
    "SEISMIC_TOSS": {
        "name": "Seismic Toss",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast X votes. X is equal to your block.",
    },
    "CHAOS": {
        "name": "Chaos",
        "rarity": "common",
        "cost": 1,
        "target": "none",
        "description": "Draw 1 card and play it for 0E.",
    },
    "STEEL_OCEAN": {
        "name": "Steel Ocean",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote and gain 1 block.",
    },
    "POUND_VOTE": {
        "name": "Pound Vote",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote and draw 1 card.",
    },
    "BRING_IT_ON": {
        "name": "Bring It On",
        "rarity": "common",
        "cost": 1,
        "target": "self",
        "description": "Gain 2 blocks and draw 1 card.",
    },
    "FLIP": {
        "name": "Flip",
        "rarity": "common",
        "cost": 1,
        "target": "self",
        "description": "Gain 1 block and draw 2 cards.",
    },
    "BATTLE_CRY": {
        "name": "Battle Cry",
        "rarity": "common",
        "cost": 0,
        "target": "none",
        "description": "Draw 2 cards. Then put a card from your hand on top of your draw pile.",
    },
    "BLIND_VOTE": {
        "name": "Blind Vote",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 3 votes. Add a curse card to your draw pile.",
    },
    "BALANCE": {
        "name": "Balance",
        "rarity": "common",
        "cost": 1,
        "target": "none",
        "description": "Draw 3 cards. Discard 1 card.",
    },
    "VOTE_THROW": {
        "name": "Vote Throw",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 2 votes. Draw 1 card. Discard 1 card.",
    },
    "VOTE_SPRAY": {
        "name": "Vote Spray",
        "rarity": "common",
        "cost": 1,
        "target": "multi_other",
        "description": "Cast 2 votes against 2 target players.",
    },
    "DE_SPRAY": {
        "name": "De-spray",
        "rarity": "common",
        "cost": 0,
        "target": "self",
        "description": "Gain 1 block. +1 block if you cast a vote.",
    },
    "ROLL_AND_DODGE": {
        "name": "Roll and Dodge",
        "rarity": "common",
        "cost": 1,
        "target": "multi_any",
        "description": "Gain 2 block. Each block can go to any player.",
    },
    "EYE_ATTACK": {
        "name": "Eye Attack",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote. Cancel 1 random card from target player.",
    },
    "SCRAPS": {
        "name": "Scraps",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote. Draw 3 cards. Discard any card with an energy cost that isn’t 0.",
    },
    "SLIM": {
        "name": "Slim",
        "rarity": "common",
        "cost": 1,
        "target": "none",
        "description": "Draw 3 cards.",
    },
    "TURBO_TIME": {
        "name": "Turbo Time",
        "rarity": "common",
        "cost": 0,
        "target": "self",
        "description": "Gain 2E. Add a curse card to your draw pile.",
    },
    "CONCENTRATE": {
        "name": "Concentrate",
        "rarity": "common",
        "cost": 0,
        "target": "multi_other",
        "description": "Cast 1 vote on 2 target players.",
    },
    "FATE": {
        "name": "Fate",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote. Scry 2. Draw 1 card.",
    },
    "FLYING_SAUCER": {
        "name": "Flying Saucer",
        "rarity": "common",
        "cost": 1,
        "target": "multi_other",
        "description": "Retain in hand if not played. Cast 1 vote on 2 target players.",
    },
    "PROTECTION": {
        "name": "Protection",
        "rarity": "common",
        "cost": 2,
        "target": "any",
        "description": "Retain in hand if not played. Gain 3 block to any player.",
    },
    "NEW_EYE": {
        "name": "New Eye",
        "rarity": "common",
        "cost": 1,
        "target": "self",
        "description": "Gain 1 block. Scry 3.",
    },

    # ===== UNCOMMONS =====
    "DOUBLE_VOTE_2E": {
        "name": "Double Vote",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 2 votes.",
    },
    "BLOCK_2": {
        "name": "Block 2",
        "rarity": "uncommon",
        "cost": 2,
        "target": "self",
        "description": "Block 2 votes.",
    },
    "ENERGY_BATTERY": {
        "name": "Energy Battery",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Next round, +1 Energy.",
    },
    "CARD_DRAW_2": {
        "name": "Card Draw 2",
        "rarity": "uncommon",
        "cost": 2,
        "target": "none",
        "description": "Draw 2 more cards this round.",
    },
    "SHARED_SHIELD": {
        "name": "Shared Shield",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_any",
        "description": "You and 1 ally each block 1 vote.",
    },
    "DRAIN_HAND": {
        "name": "Drain Hand",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cancel 1 random card from target.",
    },
    "MOMENTUM": {
        "name": "Momentum",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain +1 Energy if you played ≥2 cards this round.",
    },
    "DIG_DEEP": {
        "name": "Dig Deep",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Double your block.",
    },
    "DOUBLE_VOTE_SPLIT": {
        "name": "Double Vote (Split)",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_other",
        "description": "Cast 1 vote on 2 different players.",
    },
    "PROACTIVE": {
        "name": "Proactive",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Draw 1 card for each curse card in your hand.",
    },
    "DRAGON_FIRE": {
        "name": "Dragon Fire",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cast 3 votes for each curse card in your hand.",
    },
    "ARMORIZE": {
        "name": "Armorize",
        "rarity": "uncommon",
        "cost": 1,
        "target": "any",
        "description": "Target player gains 2 block.",
    },
    "POWER_VORTEX": {
        "name": "Power Vortex",
        "rarity": "uncommon",
        "cost": 2,
        "target": "self",
        "description": "Block all votes against you. Add a curse card to your draw pile.",
    },
    "ROAR": {
        "name": "Roar",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain 1 block for each Vote card in your hand.",
    },
    "RISKY_BUSINESS": {
        "name": "Risky Business",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Each vote cast also casts an additional vote. Receive an additional vote for each vote received.",
    },
    "FLAME_ON": {
        "name": "Flame On",
        "rarity": "uncommon",
        "cost": 2,
        "target": "none",
        "description": "Each vote cast also casts an additional vote.",
    },
    "TORNADO": {
        "name": "Tornado",
        "rarity": "uncommon",
        "cost": "X",
        "target": "other",
        "description": "Cast 1 vote X times.",
    },
    "ALL_OUT_VOTE": {
        "name": "All Out Vote",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_other",
        "description": "Cast 2 votes. Each vote may have a different target. Discard 1 card.",
    },
    "BLURRYFACE": {
        "name": "Blurryface",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain 2 blocks. +1 block if you discarded a card this turn.",
    },
    "BOUNCING_VOTE": {
        "name": "Bouncing Vote",
        "rarity": "uncommon",
        "cost": 2,
        "target": "multi_other",
        "description": "Cast 3 votes. Each vote may have a different target.",
    },
    "GAMBLE": {
        "name": "Gamble",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Discard your hand, then draw that many cards.",
    },
    "THINKER": {
        "name": "Thinker",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Discard any number of cards. Gain block for each card discarded.",
    },
    "CRIPPLING_FEAR": {
        "name": "Crippling Fear",
        "rarity": "uncommon",
        "cost": 2,
        "target": "multi_other",
        "description": "Cast 1 vote on 2 target players. Cancel 1 random card from each target player.",
    },
    "NEGOTIATE": {
        "name": "Negotiate",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cancel 2 random cards from target player.",
    },
    "SPEED": {
        "name": "Speed",
        "rarity": "uncommon",
        "cost": 2,
        "target": "self",
        "description": "Cast 2 votes and gain 2 blocks.",
    },
    "ESCAPE": {
        "name": "Escape",
        "rarity": "uncommon",
        "cost": 0,
        "target": "self",
        "description": "Gain 1 block. Draw 1 card.",
    },
    "EXPERT": {
        "name": "Expert",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Draw cards until you have 5 in your hand.",
    },
    "FINISH": {
        "name": "Finish",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote for each vote card played.",
    },
    "FLETCHING": {
        "name": "Fletching",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain 1 block for each non-vote card in your hand.",
    },
    "DEXTERITY": {
        "name": "Dexterity",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Retain in hand if not played. Each Vote card and block card gains +1.",
    },
    "INFINITE_VOTE": {
        "name": "Infinite Vote",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Retain in hand if not played. Cast 2 votes.",
    },
    "SWEEP": {
        "name": "Sweep",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Gain 3 blocks. Cancel 1 random card from target player.",
    },
    "NAUSEA": {
        "name": "Nausea",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_other",
        "description": "Retain in hand if not played. Cast 1 vote on 2 target players.",
    },
    "MANEUVER": {
        "name": "Maneuver",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Retain in hand if not played. If retained from last turn, gain 2E.",
    },
    "PIERCING_WALL": {
        "name": "Piercing Wall",
        "rarity": "uncommon",
        "cost": 2,
        "target": "multi_other",
        "description": "Gain 3 blocks. Cancel 1 random card from 2 target players.",
    },
    "CARNIVORE": {
        "name": "Carnivore",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 3 votes. Draw 2 cards.",
    },
    "BACKPACK": {
        "name": "Backpack",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Draw 1 card. Discard 1 card.",
    },
    "MIRROR": {
        "name": "Mirror",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "If this card is discarded by a card’s effect, draw 2 cards.",
    },
    "RIDDLER": {
        "name": "Riddler",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 4 votes.",
    },
    "SLASH": {
        "name": "Slash",
        "rarity": "uncommon",
        "cost": 0,
        "target": "other",
        "description": "Cast 1 vote.",
    },
    "SNEAKY_VOTE": {
        "name": "Sneaky Vote",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 2 votes. If you discarded a card this turn gain 2E.",
    },
    "MAP": {
        "name": "Map",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "If this card is discarded by a card’s effect, gain 2E.",
    },
    "SKEW": {
        "name": "Skew",
        "rarity": "uncommon",
        "cost": "X",
        "target": "other",
        "description": "Cast 1 vote X times.",
    },
    "PLAN_AHEAD": {
        "name": "Plan Ahead",
        "rarity": "uncommon",
        "cost": 2,
        "target": "none",
        "description": "Retain in hand if not played. You may retain any cards in your hand.",
    },
    "HEATSEEKER": {
        "name": "Heatseeker",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Retain in hand if not played. If you retain a separate card from last turn, draw 2 cards.",
    },
    "HOLLOW": {
        "name": "Hollow",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain 1 block. Put a card from your discard pile into your hand.",
    },
    "JUMP": {
        "name": "Jump",
        "rarity": "uncommon",
        "cost": 1,
        "target": "any",
        "description": "Gain 2 blocks to any player.",
    },
    "MACHINE": {
        "name": "Machine",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Retain in hand if not played. Draw 1 card.",
    },
    "MELT": {
        "name": "Melt",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Remove all block from target player then cast 2 vote.",
    },
    "OVERLOAD": {
        "name": "Overload",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Draw 3 cards. Add a curse card to your draw pile.",
    },
    "TRASH": {
        "name": "Trash",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Discard a card. Gain energy equal to its cost. If it costs X, instead double your energy.",
    },
    "REINFORCEMENTS": {
        "name": "Reinforcements",
        "rarity": "uncommon",
        "cost": "X",
        "target": "multi_any",
        "description": "Gain 1 block X times.",
    },
    "HOOK_LINE_SINKER": {
        "name": "Hook Line Sinker",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Retain in hand if not played. Cast 3 votes. Costs 1 energy less for each round retained.",
    },
    "SWEEP_LEG": {
        "name": "Sweep Leg",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_other",
        "description": "Cast 1 vote on 2 target players. Draw 1 card.",
    },
    "CONCLUSION": {
        "name": "Conclusion",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_other",
        "description": "You may not draw cards or gain additional energy this round. Cast 2 votes on 2 target players.",
    },
    "INFLUENCER": {
        "name": "Influencer",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 2 votes or copy another Vote card in your hand.",
    },
    "FORESIGHT": {
        "name": "Foresight",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Retain in hand if not played. Scry 3.",
    },
    "PEACEMAKER": {
        "name": "Peacemaker",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Retain in hand if not played. Whenever you scry gain 1 block.",
    },
    "CONTINUE": {
        "name": "Continue",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Retain in hand if not played. Gain 1 block. +1 block if this was retained from last round.",
    },
    "FORWARD": {
        "name": "Forward",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain 1 block. Gain 1 energy.",
    },
    "REACH": {
        "name": "Reach",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote. +1 vote for each unspent energy.",
    },
    "TIMESTONE": {
        "name": "Timestone",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Retain in hand if not played. Cast 3 votes. +1 vote for each card with Retain effect in your hand.",
    },
    "TOMBSTONE": {
        "name": "Tombstone",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 4 votes. Can only be played if this is the only Vote card in your hand.",
    },
    "TURN_AROUND": {
        "name": "Turn Around",
        "rarity": "uncommon",
        "cost": 2,
        "target": "any",
        "description": "Gain 2 block to any player. The next vote card you play costs 0E.",
    },
    "HAND_STOP": {
        "name": "Hand Stop",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cast 2 votes. Gain 1 block for each unspent energy you have.",
    },
    "WALRUS": {
        "name": "Walrus",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 2 votes. Gain block equal to the number of votes cast this round.",
    },
    "WEAVER": {
        "name": "Weaver",
        "rarity": "uncommon",
        "cost": 0,
        "target": "other",
        "description": "Cast 1 vote. If you would discard this card while scrying, instead play it and cast +3 votes.",
    },
    "WINDMILL_VOTE": {
        "name": "Windmill Vote",
        "rarity": "uncommon",
        "cost": 2,
        "target": "multi_other",
        "description": "Retain in hand if not played. Cast 2 votes. Cast +3 votes if this was retained from last round.",
    },

    # ===== STARTER UPGRADES =====
    "BASE_VOTE_UG": {
        "name": "Base Vote +",
        "rarity": "starter",
        "cost": 1,
        "target": "other",
        "description": "Cast 2 votes.",
    },
    "BLOCK_1_UG": {
        "name": "Block 1 +",
        "rarity": "starter",
        "cost": 1,
        "target": "self",
        "description": "Block 2 votes against you.",
    },
    "ASSIST_ALLY_UG": {
        "name": "Assist Ally +",
        "rarity": "starter",
        "cost": 1,
        "target": "other",
        "description": "Give 2 extra votes to another player. They secretly choose who the votes go to.",
    },
    "BLOCK_ALLY_UG": {
        "name": "Block Ally +",
        "rarity": "starter",
        "cost": 1,
        "target": "other",
        "description": "Give 2 blocks to another player.",
    },
    "PEEK_UG": {
        "name": "Peek +",
        "rarity": "starter",
        "cost": 0,
        "target": "other",
        "description": "Secretly look at another player’s hand.",
    },
    "SURVIVE_UG": {
        "name": "Survive +",
        "rarity": "starter",
        "cost": 1,
        "target": "self",
        "description": "Gain 3 blocks. Discard 1 card.",
    },
    "WEAKEN_UG": {
        "name": "Weaken +",
        "rarity": "starter",
        "cost": 0,
        "target": "other",
        "description": "Cancel 1 random card from target player.",
    },

    # ===== COMMON UPGRADES =====
    "PLUS_ONE_VOTE_UG": {
        "name": "+1 Vote +",
        "rarity": "common",
        "cost": 0,
        "target": "other",
        "description": "Cast 1 vote.",
    },
    "SHIELD_UG": {
        "name": "Shield +",
        "rarity": "common",
        "cost": 0,
        "target": "self",
        "description": "Block 1 vote.",
    },
    "QUICK_DRAW_UG": {
        "name": "Quick Draw +",
        "rarity": "common",
        "cost": 1,
        "target": "none",
        "description": "Draw 3 cards.",
    },
    "ENERGY_SURGE_UG": {
        "name": "Energy Surge +",
        "rarity": "common",
        "cost": 0,
        "target": "self",
        "description": "Gain +2 Energy this round.",
    },
    "PRESSURE_VOTE_UG": {
        "name": "Pressure Vote +",
        "rarity": "common",
        "cost": 0,
        "target": "other",
        "description": "Cast 2 votes that must be revealed publicly.",
    },
    "GROUP_TALK_UG": {
        "name": "Group Talk +",
        "rarity": "common",
        "cost": 1,
        "target": "none",
        "description": "Reveal all cards you played this round to all players; gain +2 card next round.",
    },
    "SEISMIC_TOSS_UG": {
        "name": "Seismic Toss +",
        "rarity": "common",
        "cost": 0,
        "target": "other",
        "description": "Cast X votes. X is equal to your block.",
    },
    "CHAOS_UG": {
        "name": "Chaos +",
        "rarity": "common",
        "cost": 0,
        "target": "none",
        "description": "Draw 1 card and play it for 0E.",
    },
    "STEEL_OCEAN_UG": {
        "name": "Steel Ocean +",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 2 votes and gain 2 blocks.",
    },
    "POUND_VOTE_UG": {
        "name": "Pound Vote +",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote and draw 2 cards.",
    },
    "BRING_IT_ON_UG": {
        "name": "Bring It On +",
        "rarity": "common",
        "cost": 1,
        "target": "self",
        "description": "Gain 3 blocks and draw 1 card.",
    },
    "FLIP_UG": {
        "name": "Flip +",
        "rarity": "common",
        "cost": 1,
        "target": "self",
        "description": "Gain 1 block and draw 3 cards.",
    },
    "BATTLE_CRY_UG": {
        "name": "Battle Cry +",
        "rarity": "common",
        "cost": 0,
        "target": "none",
        "description": "Draw 3 cards. Then put a card from your hand on top of your draw pile.",
    },
    "BLIND_VOTE_UG": {
        "name": "Blind Vote +",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 4 votes. Add a curse card to your draw pile.",
    },
    "BALANCE_UG": {
        "name": "Balance +",
        "rarity": "common",
        "cost": 1,
        "target": "none",
        "description": "Draw 4 cards. Discard 1 card.",
    },
    "VOTE_THROW_UG": {
        "name": "Vote Throw +",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 3 votes. Draw 1 card. Discard 1 card.",
    },
    "VOTE_SPRAY_UG": {
        "name": "Vote Spray +",
        "rarity": "common",
        "cost": 1,
        "target": "multi_other",
        "description": "Cast 3 votes against 2 target players.",
    },
    "DE_SPRAY_UG": {
        "name": "De-spray +",
        "rarity": "common",
        "cost": 0,
        "target": "self",
        "description": "Gain 1 block. +3 block if you cast a vote.",
    },
    "ROLL_AND_DODGE_UG": {
        "name": "Roll and Dodge +",
        "rarity": "common",
        "cost": 1,
        "target": "multi_any",
        "description": "Gain 3 block. Each block can go to any player.",
    },
    "EYE_ATTACK_UG": {
        "name": "Eye Attack +",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 2 votes. Cancel 1 random card from target player.",
    },
    "SCRAPS_UG": {
        "name": "Scraps +",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote. Draw 4 cards. Discard any card with an energy cost that isn’t 0.",
    },
    "SLIM_UG": {
        "name": "Slim +",
        "rarity": "common",
        "cost": 1,
        "target": "none",
        "description": "Draw 4 cards.",
    },
    "TURBO_TIME_UG": {
        "name": "Turbo Time +",
        "rarity": "common",
        "cost": 0,
        "target": "self",
        "description": "Gain 3E. Add a curse card to your draw pile.",
    },
    "CONCENTRATE_UG": {
        "name": "Concentrate +",
        "rarity": "common",
        "cost": 0,
        "target": "multi_other",
        "description": "Cast 2 votes on 2 target players.",
    },
    "FATE_UG": {
        "name": "Fate +",
        "rarity": "common",
        "cost": 1,
        "target": "other",
        "description": "Cast 1 vote. Scry 3. Draw 1 card.",
    },
    "FLYING_SAUCER_UG": {
        "name": "Flying Saucer +",
        "rarity": "common",
        "cost": 0,
        "target": "multi_other",
        "description": "Retain in hand if not played. Cast 1 vote on 2 target players.",
    },
    "PROTECTION_UG": {
        "name": "Protection +",
        "rarity": "common",
        "cost": 2,
        "target": "any",
        "description": "Retain in hand if not played. Gain 4 block to any player.",
    },
    "NEW_EYE_UG": {
        "name": "New Eye +",
        "rarity": "common",
        "cost": 0,
        "target": "self",
        "description": "Gain 1 block. Scry 3.",
    },

    # ===== UNCOMMON UPGRADES =====
    "DOUBLE_VOTE_2E_UG": {
        "name": "Double Vote +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 3 votes.",
    },
    "BLOCK_2z_UG": {
        "name": "Block 2 +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Block 2 votes.",
    },
    "ENERGY_BATTERY_UG": {
        "name": "Energy Battery +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "self",
        "description": "Next round, +1 Energy.",
    },
    "CARD_DRAW_2_UG": {
        "name": "Card Draw 2 +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Draw 2 more cards this round.",
    },
    "SHARED_SHIELD_UG": {
        "name": "Shared Shield +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_any",
        "description": "You and 1 ally each block 2 votes.",
    },
    "DRAIN_HAND_UG": {
        "name": "Drain Hand +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cancel 1 random card from target.",
    },
    "MOMENTUM_UG": {
        "name": "Momentum +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "self",
        "description": "Gain +1 Energy if you played ≥2 cards this round.",
    },
    "DIG_DEEP_UG": {
        "name": "Dig Deep +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "self",
        "description": "Double your block.",
    },
    "DOUBLE_VOTE_SPLIT_UG": {
        "name": "Double Vote (Split) +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_other",
        "description": "Cast 2 votes on 2 different players.",
    },
    "PROACTIVE_UG": {
        "name": "Proactive +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Draw 2 cards for each curse card in your hand.",
    },
    "DRAGON_FIRE_UG": {
        "name": "Dragon Fire +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cast 5 votes for each curse card in your hand.",
    },
    "ARMORIZE_UG": {
        "name": "Armorize +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "any",
        "description": "Target player gains 3 block.",
    },
    "POWER_VORTEX_UG": {
        "name": "Power Vortex +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Block all votes against you. Add a curse card to your draw pile.",
    },
    "ROAR_UG": {
        "name": "Roar +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain 2 block for each Vote card in your hand.",
    },
    "RISKY_BUSINESS_UG": {
        "name": "Risky Business +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Each vote cast also casts an additional vote. Receive an additional vote for each vote received.",
    },
    "FLAME_ON_UG": {
        "name": "Flame On +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Each vote cast also casts an additional vote.",
    },
    "TORNADO_UG": {
        "name": "Tornado +",
        "rarity": "uncommon",
        "cost": "X",
        "target": "other",
        "description": "Cast 1 vote X+1 times.",
    },
    "ALL_OUT_VOTE_UG": {
        "name": "All Out Vote +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_other",
        "description": "Cast 3 votes. Each vote may have a different target. Discard 1 card.",
    },
    "BLURRYFACE_UG": {
        "name": "Blurryface +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain 3 blocks. +1 block if you discarded a card this turn.",
    },
    "BOUNCING_VOTE_UG": {
        "name": "Bouncing Vote +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "multi_other",
        "description": "Cast 5 votes. Each vote may have a different target.",
    },
    "GAMBLE_UG": {
        "name": "Gamble +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Discard your hand, then draw that many cards.",
    },
    "THINKER_UG": {
        "name": "Thinker +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "self",
        "description": "Discard any number of cards. Gain block for each card discarded.",
    },
    "CRIPPLING_FEAR_UG": {
        "name": "Crippling Fear +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "multi_other",
        "description": "Cast 2 votes on 2 target players. Cancel 1 random card from each target player.",
    },
    "NEGOTIATE_UG": {
        "name": "Negotiate +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "other",
        "description": "Cancel 2 random cards from target player.",
    },
    "SPEED_UG": {
        "name": "Speed +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "self",
        "description": "Cast 4 votes and gain 4 blocks.",
    },
    "ESCAPE_UG": {
        "name": "Escape +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "self",
        "description": "Gain 2 block. Draw 1 card.",
    },
    "EXPERT_UG": {
        "name": "Expert +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Draw cards until you have 6 in your hand.",
    },
    "FINISH_UG": {
        "name": "Finish +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cast 2 votes for each vote card played.",
    },
    "FLETCHING_UG": {
        "name": "Fletching +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain 2 block for each non-vote card in your hand.",
    },
    "DEXTERITY_UG": {
        "name": "Dexterity +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Retain in hand if not played. Each Vote card and block card gains +2.",
    },
    "INFINITE_VOTE_UG": {
        "name": "Infinite Vote +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Retain in hand if not played. Cast 3 votes.",
    },
    "SWEEP_UG": {
        "name": "Sweep +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Gain 4 blocks. Cancel 1 random card from target player.",
    },
    "NAUSEA_UG": {
        "name": "Nausea +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_other",
        "description": "Retain in hand if not played. Cast 2 votes on 2 target players.",
    },
    "MANEUVER_UG": {
        "name": "Maneuver +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Retain in hand if not played. If retained from last turn, gain 3E.",
    },
    "PIERCING_WALL_UG": {
        "name": "Piercing Wall +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "multi_other",
        "description": "Gain 4 blocks. Cancel 1 random card from 2 target players.",
    },
    "CARNIVORE_UG": {
        "name": "Carnivore +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cast 3 votes. Draw 2 cards.",
    },
    "BACKPACK_UG": {
        "name": "Backpack +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Draw 2 cards. Discard 2 cards.",
    },
    "MIRROR_UG": {
        "name": "Mirror +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "If this card is discarded by a card’s effect, draw 3 cards.",
    },
    "RIDDLER_UG": {
        "name": "Riddler +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 6 votes.",
    },
    "SLASH_UG": {
        "name": "Slash +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "other",
        "description": "Cast 2 votes.",
    },
    "SNEAKY_VOTE_UG": {
        "name": "Sneaky Vote +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 4 votes. If you discarded a card this turn gain 2E.",
    },
    "MAP_UG": {
        "name": "Map +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "If this card is discarded by a card’s effect, gain 3E.",
    },
    "SKEW_UG": {
        "name": "Skew +",
        "rarity": "uncommon",
        "cost": "X",
        "target": "other",
        "description": "Cast 2 votes X times.",
    },
    "PLAN_AHEAD_UG": {
        "name": "Plan Ahead +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Retain in hand if not played. You may retain any cards in your hand.",
    },
    "HEATSEEKER_UG": {
        "name": "Heatseeker +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Retain in hand if not played. If you retain a separate card from last turn, draw 3 cards.",
    },
    "HOLLOW_UG": {
        "name": "Hollow +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain 2 block. Put a card from your discard pile into your hand.",
    },
    "JUMP_UG": {
        "name": "Jump +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "any",
        "description": "Gain 3 blocks to any player.",
    },
    "MACHINE_UG": {
        "name": "Machine +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Retain in hand if not played. Draw 2 cards.",
    },
    "MELT_UG": {
        "name": "Melt +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Remove all block from target player then cast 2 vote.",
    },
    "OVERLOAD_UG": {
        "name": "Overload +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Draw 4 cards. Add a curse card to your draw pile.",
    },
    "TRASH_UG": {
        "name": "Trash +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Discard a card. Gain energy equal to its cost. If it costs X, instead double your energy.",
    },
    "REINFORCEMENTS_UG": {
        "name": "Reinforcements +",
        "rarity": "uncommon",
        "cost": "X",
        "target": "multi_any",
        "description": "Gain 1 block X+1 times.",
    },
    "HOOK_LINE_SINKER_UG": {
        "name": "Hook Line Sinker +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Retain in hand if not played. Cast 4 votes. Costs 1 energy less for each round retained.",
    },
    "SWEEP_LEG_UG": {
        "name": "Sweep Leg +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_other",
        "description": "Cast 1 vote on 2 target players. Draw 2 cards.",
    },
    "CONCLUSION_UG": {
        "name": "Conclusion +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "multi_other",
        "description": "You may not draw cards or gain additional energy this round. Cast 3 votes on 2 target players.",
    },
    "INFLUENCER_UG": {
        "name": "Influencer +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cast 2 votes or copy another Vote card in your hand.",
    },
    "FORESIGHT_UG": {
        "name": "Foresight +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "none",
        "description": "Retain in hand if not played. Scry 4.",
    },
    "PEACEMAKER_UG": {
        "name": "Peacemaker +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "none",
        "description": "Retain in hand if not played. Whenever you scry gain 2 block.",
    },
    "CONTINUE_UG": {
        "name": "Continue +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Retain in hand if not played. Gain 2 block. +1 block if this was retained from last round.",
    },
    "FORWARD_UG": {
        "name": "Forward +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "self",
        "description": "Gain 1 block. Gain 2 energy.",
    },
    "REACH_UG": {
        "name": "Reach +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cast 2 votes. +1 vote for each unspent energy.",
    },
    "TIMESTONE_UG": {
        "name": "Timestone +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Retain in hand if not played. Cast 5 votes. +1 vote for each card with Retain effect in your hand.",
    },
    "TOMBSTONE_UG": {
        "name": "Tombstone +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "other",
        "description": "Cast 6 votes. Can only be played if this is the only Vote card in your hand.",
    },
    "TURN_AROUND_UG": {
        "name": "Turn Around +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "any",
        "description": "Gain 2 block to any player. The next vote card you play costs 0E.",
    },
    "HAND_STOP_UG": {
        "name": "Hand Stop +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "other",
        "description": "Cast 2 votes. Gain 1 block for each unspent energy you have.",
    },
    "WALRUS_UG": {
        "name": "Walrus +",
        "rarity": "uncommon",
        "cost": 1,
        "target": "other",
        "description": "Cast 2 votes. Gain block equal to the number of votes cast this round.",
    },
    "WEAVER_UG": {
        "name": "Weaver +",
        "rarity": "uncommon",
        "cost": 0,
        "target": "other",
        "description": "Cast 2 votes. If you would discard this card while scrying, instead play it and cast +3 votes.",
    },
    "WINDMILL_VOTE_UG": {
        "name": "Windmill Vote +",
        "rarity": "uncommon",
        "cost": 2,
        "target": "multi_other",
        "description": "Retain in hand if not played. Cast 4 votes. Cast +3 votes if this was retained from last round.",
    },
}

# Default starter deck (10 cards)
STARTER_DECK_DEFAULT = [
    "BASE_VOTE",
    "BASE_VOTE",
    "BASE_VOTE",
    "BASE_VOTE",
    "BLOCK_1",
    "ASSIST_ALLY",
    "BLOCK_ALLY",
    "PEEK",
    "SURVIVE",
    "WEAKEN",
]

# Build upgrade map based on *_UG cards
UPGRADE_MAP: Dict[str, str] = {}
for cid in CARD_CATALOG.keys():
    if cid.endswith("_UG"):
        base = cid[:-3]
        if base in CARD_CATALOG:
            UPGRADE_MAP[base] = cid

# Special-case typo'd id if needed
if "BLOCK_2" in CARD_CATALOG and "BLOCK_2z_UG" in CARD_CATALOG:
    UPGRADE_MAP["BLOCK_2"] = "BLOCK_2z_UG"


# =========================
# Core Data Structures
# =========================

@dataclass
class PlayerState:
    user_id: int
    username: str
    alive: bool = True
    deck: List[str] = field(default_factory=list)
    discard: List[str] = field(default_factory=list)
    hand: List[str] = field(default_factory=list)
    energy_max: int = 3
    energy: int = 3
    blocks: int = 0
    votes_cast_this_round: int = 0
    votes_received_this_round: int = 0
    # Buffs for next round etc.
    next_round_extra_cards: int = 0
    next_round_energy_bonus: int = 0
    # For retain-related effects
    retained_last_round: Dict[str, bool] = field(default_factory=dict)
    # Phase flags
    turn_done: bool = False
    draft_done: bool = False
    camp_done: bool = False
    # Tracking for more advanced effects
    cards_played_this_round: List[str] = field(default_factory=list)
    cards_discarded_this_round: List[str] = field(default_factory=list)


@dataclass
class Action:
    source_id: int
    card_id: str
    target_id: Optional[int] = None
    x_value: int = 0  # for X-cost cards


@dataclass
class GameState:
    chat_id: int
    host_id: int
    round_number: int = 0
    joining_open: bool = True
    phase: str = "lobby"  # lobby, playing, drafting, camp, finished
    players: Dict[int, PlayerState] = field(default_factory=dict)
    actions: List[Action] = field(default_factory=list)
    reward_offers: Dict[int, List[str]] = field(default_factory=dict)


# chat_id -> GameState
GAMES: Dict[int, GameState] = {}

# player_id -> chat_id (so DMs know which game you belong to)
PLAYER_TO_GAME: Dict[int, int] = {}


# =========================
# Helper / Utility
# =========================

def get_game(chat_id: int) -> Optional[GameState]:
    return GAMES.get(chat_id)


def get_game_for_player(user_id: int) -> Optional[GameState]:
    chat_id = PLAYER_TO_GAME.get(user_id)
    if chat_id is None:
        return None
    return GAMES.get(chat_id)


def require_game(func):
    """Decorator to ensure a game exists for the chat (group commands)."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat = update.effective_chat
        if not chat:
            return
        if chat.type == "private":
            await update.effective_message.reply_text("Use this command in the group game chat.")
            return
        game = get_game(chat.id)
        if not game:
            await update.effective_message.reply_text("No game in this chat. Use /newgame to start.")
            return
        return await func(update, context, game)
    return wrapper


def card_name(card_id: str) -> str:
    return CARD_CATALOG.get(card_id, {}).get("name", card_id)


def card_cost(card_id: str):
    return CARD_CATALOG.get(card_id, {}).get("cost", 1)


def card_desc(card_id: str) -> str:
    return CARD_CATALOG.get(card_id, {}).get("description", "")


def card_has_retain(card_id: str) -> bool:
    desc = CARD_CATALOG.get(card_id, {}).get("description", "").lower()
    return "retain in hand if not played" in desc


def is_vote_card(card_id: str) -> bool:
    """Very simple heuristic: card whose description starts with/contains 'Cast' and 'vote'."""
    desc = card_desc(card_id).lower()
    return "cast" in desc and "vote" in desc


def draw_one(player: PlayerState):
    """Draw a single card; reshuffle discard if deck is empty."""
    if not player.deck and player.discard:
        tmp = list(player.discard)
        player.discard.clear()
        random.shuffle(tmp)
        player.deck.extend(tmp)
    if player.deck:
        card = player.deck.pop()
        player.hand.append(card)
        return card
    return None


def draw_cards(player: PlayerState, n: int):
    drawn = []
    for _ in range(max(0, n)):
        c = draw_one(player)
        if c is None:
            break
        drawn.append(c)
    return drawn


def discard_random(player: PlayerState, count: int = 1):
    """Discard random cards from hand."""
    for _ in range(max(0, count)):
        if not player.hand:
            return
        idx = random.randrange(len(player.hand))
        cid = player.hand.pop(idx)
        player.discard.append(cid)
        player.cards_discarded_this_round.append(cid)


def format_hand(player: PlayerState) -> str:
    lines = [f"Energy: {player.energy}/{player.energy_max}", "Your hand:"]
    if not player.hand:
        lines.append(" - (empty)")
    else:
        for idx, cid in enumerate(player.hand):
            cost = card_cost(cid)
            cost_str = "X" if cost == "X" else ("-" if cost is None else str(cost))
            lines.append(f"{idx+1}. {card_name(cid)} (cost {cost_str})")
    return "\n".join(lines)


def list_alive_players(game: GameState) -> List[PlayerState]:
    return [p for p in game.players.values() if p.alive]


def list_common_uncommon_ids() -> List[str]:
    ids = []
    for cid, data in CARD_CATALOG.items():
        if data.get("rarity") in ("common", "uncommon"):
            ids.append(cid)
    return ids


# =========================
# Simple vote/block maps used in /resolve
# (These are the cards that actually change vote/block totals.)
# =========================

VOTE_CARDS_SIMPLE: Dict[str, int] = {
    # Starters
    "BASE_VOTE": 1,
    "BASE_VOTE_UG": 2,
    # Commons
    "PLUS_ONE_VOTE": 1,
    "PLUS_ONE_VOTE_UG": 1,
    "POUND_VOTE": 1,
    "POUND_VOTE_UG": 1,
    "PRESSURE_VOTE": 1,
    "PRESSURE_VOTE_UG": 2,
    "DOUBLE_VOTE_2E": 2,
    "DOUBLE_VOTE_2E_UG": 3,
    "DOUBLE_VOTE_SPLIT": 2,
    "DOUBLE_VOTE_SPLIT_UG": 4,
    "BLIND_VOTE": 3,
    "BLIND_VOTE_UG": 4,
    "VOTE_THROW": 2,
    "VOTE_THROW_UG": 3,
    "VOTE_SPRAY": 2,
    "VOTE_SPRAY_UG": 3,
    "CONCENTRATE": 2,
    "CONCENTRATE_UG": 4,
    "RIDDLER": 4,
    "RIDDLER_UG": 6,
    "SLASH": 1,
    "SLASH_UG": 2,
    "INFINITE_VOTE": 2,
    "INFINITE_VOTE_UG": 3,
    "CARNIVORE": 3,
    "CARNIVORE_UG": 3,
    "SWEEP_LEG": 2,
    "SWEEP_LEG_UG": 2,
    "CONCLUSION": 4,      # 2 votes on 2 players -> 4 total
    "CONCLUSION_UG": 6,   # 3 votes on 2 players
    "WINDMILL_VOTE": 2,
    "WINDMILL_VOTE_UG": 4,
}

BLOCK_CARDS_SIMPLE: Dict[str, int] = {
    "BLOCK_1": 1,
    "BLOCK_1_UG": 2,
    "SHIELD": 1,
    "SHIELD_UG": 1,
    "BLOCK_2": 2,
    "BLOCK_2z_UG": 2,
    "SURVIVE": 2,
    "SURVIVE_UG": 3,
    "BRING_IT_ON": 2,
    "BRING_IT_ON_UG": 3,
    "FLIP": 1,
    "FLIP_UG": 1,
    "DE_SPRAY": 1,
    "DE_SPRAY_UG": 3,
    "ROLL_AND_DODGE": 2,
    "ROLL_AND_DODGE_UG": 3,
    "PROTECTION": 3,
    "PROTECTION_UG": 4,
    "ARMORIZE": 2,
    "ARMORIZE_UG": 3,
    "SPEED": 2,
    "SPEED_UG": 4,
    "ESCAPE": 1,
    "ESCAPE_UG": 2,
    "FLETCHING": 1,   # per non-vote, but we just treat as flat 1 here
    "FLETCHING_UG": 2,
    "JUMP": 2,
    "JUMP_UG": 3,
    "PIERCING_WALL": 3,
    "PIERCING_WALL_UG": 4,
    "SWEEP": 3,
    "SWEEP_UG": 4,
    "CONTINUE": 1,
    "CONTINUE_UG": 2,
    "FORWARD": 1,
    "FORWARD_UG": 1,
    "HAND_STOP": 1,
    "HAND_STOP_UG": 1,
    "WALRUS": 2,
    "WALRUS_UG": 2,
}


# =========================
# Commands: Group
# =========================

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎮 *Last Hand Standing – Commands*\n\n"
        "*Group commands:*\n"
        "/newgame – Start a new game in this group\n"
        "/join – Join the current game\n"
        "/startgame – Initialize decks (host only)\n"
        "/nextround – Begin the next round (host only)\n"
        "/resolve – Resolve all played cards and eliminate (host only)\n"
        "/players – List all players (alive & eliminated)\n"
        "/status – Show round, phase, and player status\n"
        "/readycheck – Show who hasn’t finished actions (host only)\n"
        "/camp – Camp phase: upgrade/remove a card (host only)\n"
        "/reward – Extra draft of 3 cards (host only; manual)\n"
        "/endgame – End the current game early (host only)\n\n"
        "*DM commands:*\n"
        "/start – Info & help (in DM)\n"
        "/deck – View your deck\n"
        "/remove N – Remove the Nth card from your deck\n"
        "/upgrade N – Upgrade the Nth card in your deck\n"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown")


async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private":
        await update.effective_message.reply_text("Please use /newgame in a GROUP chat.")
        return

    GAMES[chat.id] = GameState(chat_id=chat.id, host_id=user.id)
    await update.effective_message.reply_text(
        f"🎮 New Last Hand Standing game created by {user.mention_html()}!\n"
        "Players can now /join.\n"
        "When ready, host can /startgame and then /nextround.",
        parse_mode="HTML",
    )


@require_game
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    user = update.effective_user
    if not game.joining_open:
        await update.effective_message.reply_text("Joining is closed for this game.")
        return
    if user.id in game.players:
        await update.effective_message.reply_text("You are already in the game.")
        return

    username = user.full_name or user.username or str(user.id)
    ps = PlayerState(user_id=user.id, username=username)
    game.players[user.id] = ps
    PLAYER_TO_GAME[user.id] = game.chat_id

    await update.effective_message.reply_text(
        f"{username} has joined the game! ({len(game.players)} players total)"
    )


@require_game
async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    user = update.effective_user
    if user.id != game.host_id:
        await update.effective_message.reply_text("Only the host can start the game.")
        return
    if len(game.players) < 2:
        await update.effective_message.reply_text("Need at least 2 players to start.")
        return

    game.joining_open = False
    game.round_number = 0
    game.phase = "lobby"

    for p in game.players.values():
        p.deck = STARTER_DECK_DEFAULT.copy()
        random.shuffle(p.deck)
        p.discard = []
        p.hand = []
        p.energy_max = 3
        p.energy = 3
        p.blocks = 0
        p.turn_done = False
        p.draft_done = False
        p.camp_done = False
        p.next_round_extra_cards = 0
        p.next_round_energy_bonus = 0
        p.cards_played_this_round.clear()
        p.cards_discarded_this_round.clear()

    await update.effective_message.reply_text(
        "🃏 Game started! All players have the starter 10-card deck.\n"
        "Host can now use /nextround to begin Round 1."
    )


@require_game
async def players_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    alive = [p.username for p in game.players.values() if p.alive]
    dead = [p.username for p in game.players.values() if not p.alive]

    if not game.players:
        await update.effective_message.reply_text("No players have joined yet.")
        return

    lines = ["👥 Players in this game", ""]
    lines.append("Alive:")
    if alive:
        lines.extend(f" - {name}" for name in alive)
    else:
        lines.append(" - (none)")

    lines.append("")
    lines.append("Eliminated:")
    if dead:
        lines.extend(f" - {name}" for name in dead)
    else:
        lines.append(" - (none)")

    await update.effective_message.reply_text("\n".join(lines))


@require_game
async def nextround(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    """
    Start a new round:
    - Discard old non-retain cards
    - Keep retain cards in hand
    - Reset energy/blocks
    - Draw 5 + bonus new cards (no hand size cap)
    - DM hands
    """
    user = update.effective_user
    if user.id != game.host_id:
        await update.effective_message.reply_text("Only the host can start a new round.")
        return

    alive = list_alive_players(game)
    if len(alive) < 2:
        await update.effective_message.reply_text("Not enough players alive to continue.")
        return

    game.round_number += 1
    game.phase = "playing"
    game.actions = []

    await update.effective_message.reply_text(
        f"🔄 Starting Round {game.round_number}! Discarding non-retain cards and dealing 5 new cards..."
    )

    for p in alive:
        # Mark which retain cards stayed from last round
        new_retained = {}
        for cid in p.hand:
            if card_has_retain(cid):
                new_retained[cid] = True

        # Discard all non-retain cards in hand
        new_hand = []
        for cid in p.hand:
            if card_has_retain(cid):
                new_hand.append(cid)  # stays in hand
            else:
                p.discard.append(cid)
        p.hand = new_hand

        # Store which cards were retained (for "retained from last round" effects)
        p.retained_last_round = new_retained

        # Reset per-round stats
        p.blocks = 0
        p.votes_cast_this_round = 0
        p.votes_received_this_round = 0
        p.cards_played_this_round.clear()
        p.cards_discarded_this_round.clear()

        # Reset phase flags
        p.turn_done = False
        p.draft_done = False
        p.camp_done = False

        # Reset energy with bonus if any
        p.energy_max = 3 + p.next_round_energy_bonus
        p.energy = p.energy_max
        p.next_round_energy_bonus = 0

        # Draw 5 + extra NEW cards (no cap including retained)
        draw_count = 5 + p.next_round_extra_cards
        p.next_round_extra_cards = 0
        draw_cards(p, draw_count)

        # DM their hand
        try:
            await send_hand_menu(context, game, p)
        except Exception as e:
            logger.error(f"Failed to DM player {p.user_id}: {e}")

    await update.effective_message.reply_text(
        "Hands sent via DM. Players may now play cards until they are done. Host can /resolve at any time."
    )


@require_game
async def resolve(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    """
    Simple resolver: only basic vote/block effects are implemented so far.
    After resolving:
      - Eliminates player(s)
      - If game continues, automatically triggers drafting (like /reward)
    """
    user = update.effective_user
    if user.id != game.host_id:
        await update.effective_message.reply_text("Only the host can resolve the round.")
        return

    alive_before = list_alive_players(game)
    if len(alive_before) < 2:
        await update.effective_message.reply_text("Not enough players alive to resolve.")
        return

    # Even if some players didn't hit 'Done', we just treat them as no actions.
    if not game.actions:
        await update.effective_message.reply_text(
            "No actions were played this round. No elimination will occur."
        )
        return

    # Tally plain votes and blocks, based on simplified mapping.
    votes_on: Dict[int, int] = {}
    blocks_on: Dict[int, int] = {}

    for act in game.actions:
        cid = act.card_id
        src = act.source_id
        tgt = act.target_id

        # Simple votes
        if cid in VOTE_CARDS_SIMPLE and tgt is not None:
            count = VOTE_CARDS_SIMPLE[cid]
            votes_on[tgt] = votes_on.get(tgt, 0) + count
            game.players[src].votes_cast_this_round += count
            game.players[tgt].votes_received_this_round += count

        # Simple blocks
        if cid in BLOCK_CARDS_SIMPLE:
            # most block cards are self-targeted; for simplicity apply to source
            blocks_on[src] = blocks_on.get(src, 0) + BLOCK_CARDS_SIMPLE[cid]

        # Special starter helpers
        if cid == "ASSIST_ALLY" and tgt is not None:
            votes_on[tgt] = votes_on.get(tgt, 0) + 1
        if cid == "ASSIST_ALLY_UG" and tgt is not None:
            votes_on[tgt] = votes_on.get(tgt, 0) + 2

        if cid == "BLOCK_ALLY" and tgt is not None:
            blocks_on[tgt] = blocks_on.get(tgt, 0) + 1
        if cid == "BLOCK_ALLY_UG" and tgt is not None:
            blocks_on[tgt] = blocks_on.get(tgt, 0) + 2

    # Apply blocks: each block cancels 1 vote
    final_votes: Dict[int, int] = {}
    for pid, v in votes_on.items():
        b = blocks_on.get(pid, 0)
        final_votes[pid] = max(0, v - b)

    if not final_votes:
        await update.effective_message.reply_text(
            "After applying blocks, nobody has any votes. No one is eliminated."
        )
        return

    # Show results
    lines = ["📊 Round results:"]
    for p in list_alive_players(game):
        v = final_votes.get(p.user_id, 0)
        lines.append(f" - {p.username}: {v} vote(s)")
    await update.effective_message.reply_text("\n".join(lines))

    max_votes = max(final_votes.values())
    elim_ids = [pid for pid, v in final_votes.items() if v == max_votes]
    elim_players = [game.players[pid] for pid in elim_ids if game.players[pid].alive]

    if not elim_players:
        await update.effective_message.reply_text("No one is eliminated this round.")
    else:
        for p in elim_players:
            p.alive = False

        if len(elim_players) == 1:
            await update.effective_message.reply_text(f"❌ {elim_players[0].username} has been eliminated!")
        else:
            names = ", ".join(p.username for p in elim_players)
            await update.effective_message.reply_text(
                f"❌ Multiple players tied with {max_votes} votes and are eliminated: {names}"
            )

    alive_after = list_alive_players(game)
    if len(alive_after) == 1:
        await update.effective_message.reply_text(
            f"🏆 {alive_after[0].username} is the LAST HAND STANDING! Game over."
        )
        game.phase = "finished"
        return
    elif len(alive_after) == 0:
        await update.effective_message.reply_text("Everyone has been eliminated. Chaos victory.")
        game.phase = "finished"
        return

    # Game continues: start draft phase (3-card offers)
    await update.effective_message.reply_text(
        "📦 Round complete. Starting draft: each alive player will receive 3 random cards in DM to choose 1 or Skip."
    )
    await reward(update, context, game)  # reuse reward logic as draft
    # reward() will set phase="drafting"


@require_game
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    alive = [p for p in game.players.values() if p.alive]
    dead = [p for p in game.players.values() if not p.alive]
    lines = [
        f"🎮 Game status – Round {game.round_number}, phase: {game.phase}",
        "Alive:",
    ]
    if alive:
        lines.extend(f" - {p.username}" for p in alive)
    else:
        lines.append(" - (none)")

    lines.append("Eliminated:")
    if dead:
        lines.extend(f" - {p.username}" for p in dead)
    else:
        lines.append(" - (none)")

    await update.effective_message.reply_text("\n".join(lines))


@require_game
async def reward(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    """
    Host command (and internal helper from /resolve):
    send each alive player 3 random Common/Uncommon cards to add or skip.
    Also used as the post-/resolve draft step.
    """
    user = update.effective_user
    if user.id != game.host_id:
        await update.effective_message.reply_text("Only the host can grant rewards / start drafts.")
        return

    pool = list_common_uncommon_ids()
    if not pool:
        await update.effective_message.reply_text("No common/uncommon cards configured.")
        return

    alive = list_alive_players(game)
    if not alive:
        await update.effective_message.reply_text("No alive players to reward.")
        return

    game.reward_offers.clear()
    game.phase = "drafting"

    for p in alive:
        # sample 3 distinct cards (or with replacement if fewer in pool)
        offers = random.sample(pool, k=min(3, len(pool)))
        game.reward_offers[p.user_id] = offers
        p.draft_done = False

        buttons = []
        for cid in offers:
            buttons.append([
                InlineKeyboardButton(
                    text=f"Take {card_name(cid)}",
                    callback_data=f"reward_pick|{game.chat_id}|{p.user_id}|{cid}"
                )
            ])
        buttons.append([
            InlineKeyboardButton(
                text="Skip",
                callback_data=f"reward_skip|{game.chat_id}|{p.user_id}"
            )
        ])

        try:
            await context.bot.send_message(
                chat_id=p.user_id,
                text=(
                    "📦 Draft / Reward! Choose one card to add to your deck or skip:\n\n" +
                    "\n".join(f"- {card_name(cid)} – {card_desc(cid)}" for cid in offers)
                ),
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        except Exception as e:
            logger.error(f"Failed to send reward DM to {p.user_id}: {e}")

    await update.effective_message.reply_text(
        "Draft choices sent to all alive players via DM."
    )


@require_game
async def readycheck(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    user = update.effective_user
    if user.id != game.host_id:
        await update.effective_message.reply_text("Only the host can use /readycheck.")
        return

    phase = game.phase
    alive = list_alive_players(game)

    if phase == "playing":
        not_done = [p.username for p in alive if not p.turn_done]
        label = "turns (card plays)"
    elif phase == "drafting":
        not_done = [p.username for p in alive if not p.draft_done]
        label = "draft choices"
    elif phase == "camp":
        not_done = [p.username for p in alive if not p.camp_done]
        label = "camp choices"
    else:
        await update.effective_message.reply_text("No pending actions in the current phase.")
        return

    if not not_done:
        await update.effective_message.reply_text(f"✅ All players have finished their {label}.")
    else:
        lines = [f"⏳ Still pending {label} from:"]
        for name in not_done:
            lines.append(f" - {name}")
        await update.effective_message.reply_text("\n".join(lines))


@require_game
async def camp(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    """Host triggers camp phase: each alive player can upgrade or remove a card."""
    user = update.effective_user
    if user.id != game.host_id:
        await update.effective_message.reply_text("Only the host can start the camp phase.")
        return

    alive = list_alive_players(game)
    if not alive:
        await update.effective_message.reply_text("No alive players to send to camp.")
        return

    game.phase = "camp"
    await update.effective_message.reply_text(
        "🏕 Camp phase! Each alive player will be asked to upgrade or remove a card in DM."
    )

    for p in alive:
        p.camp_done = False
        buttons = [
            [
                InlineKeyboardButton(
                    text="⬆️ Upgrade a card", callback_data=f"camp_upgrade|{game.chat_id}|{p.user_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Remove a card", callback_data=f"camp_remove|{game.chat_id}|{p.user_id}"
                )
            ],
        ]
        try:
            await context.bot.send_message(
                chat_id=p.user_id,
                text=(
                    "🏕 You arrived at camp!\n\n"
                    "Choose whether to *upgrade* a card or *remove* a card from your deck."
                ),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to DM camp to {p.user_id}: {e}")


@require_game
async def endgame(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    user = update.effective_user
    if user.id != game.host_id:
        await update.effective_message.reply_text("Only the host can end the game early.")
        return

    await update.effective_message.reply_text("🛑 The host has ended the game early.")

    # DM all players
    for p in game.players.values():
        try:
            await context.bot.send_message(
                chat_id=p.user_id,
                text="🛑 The current Last Hand Standing game has been ended by the host.",
            )
        except Exception:
            pass

    game.phase = "finished"
    if game.chat_id in GAMES:
        del GAMES[game.chat_id]


# =========================
# Commands: Private deck management
# =========================

async def start_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm the Last Hand Standing bot.\n"
        "I run games in group chats.\n\n"
        "Useful DM commands:\n"
        " /deck – view your deck\n"
        " /remove N – remove the Nth card from your deck\n"
        " /upgrade N – upgrade the Nth card in your deck (if an upgraded version exists)\n\n"
        "In a group: use /help to see all commands."
    )


async def deck_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    game = get_game_for_player(user.id)
    if not game:
        await update.effective_message.reply_text("You are not currently in a game.")
        return

    p = game.players.get(user.id)
    if not p:
        await update.effective_message.reply_text("You are not a player in this game.")
        return

    if not p.deck:
        await update.effective_message.reply_text("Your deck is empty.")
        return

    lines = ["📦 Your deck:"]
    for i, cid in enumerate(p.deck):
        lines.append(f"{i+1}. {card_name(cid)} ({cid})")
    lines.append("\nUse /remove N or /upgrade N in this DM to modify your deck.")

    await update.effective_message.reply_text("\n".join(lines))


async def remove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    game = get_game_for_player(user.id)
    if not game:
        await update.effective_message.reply_text("You are not currently in a game.")
        return

    p = game.players.get(user.id)
    if not p:
        await update.effective_message.reply_text("You are not a player in this game.")
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /remove N   (N is the card number from /deck)")
        return

    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        await update.effective_message.reply_text("N must be a number, e.g. /remove 3")
        return

    if idx < 0 or idx >= len(p.deck):
        await update.effective_message.reply_text("Invalid card number.")
        return

    removed = p.deck.pop(idx)
    await update.effective_message.reply_text(
        f"Removed {card_name(removed)} from your deck."
    )


async def upgrade_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upgrade using the explicit *_UG cards."""
    user = update.effective_user
    game = get_game_for_player(user.id)
    if not game:
        await update.effective_message.reply_text("You are not currently in a game.")
        return

    p = game.players.get(user.id)
    if not p:
        await update.effective_message.reply_text("You are not a player in this game.")
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /upgrade N   (N is the card number from /deck)")
        return

    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        await update.effective_message.reply_text("N must be a number, e.g. /upgrade 2")
        return

    if idx < 0 or idx >= len(p.deck):
        await update.effective_message.reply_text("Invalid card number.")
        return

    old_id = p.deck[idx]
    new_id = UPGRADE_MAP.get(old_id)
    if not new_id:
        await update.effective_message.reply_text(
            f"{card_name(old_id)} does not have an upgraded version yet."
        )
        return

    p.deck[idx] = new_id
    await update.effective_message.reply_text(
        f"Upgraded {card_name(old_id)} to {card_name(new_id)}."
    )


# =========================
# Card play UI (DM)
# =========================

def is_card_playable(p: PlayerState, cid: str) -> bool:
    """Check if card can be played right now given energy and cost."""
    cost = card_cost(cid)
    if cost is None:
        # Curse/unplayable
        return False
    if cost == "X":
        return p.energy > 0
    try:
        c_int = int(cost)
    except Exception:
        c_int = 1
    return p.energy >= c_int


async def send_hand_menu(context: ContextTypes.DEFAULT_TYPE, game: GameState, p: PlayerState):
    """Send the 'play cards' menu for a player with Play + Info buttons."""
    buttons = []

    for idx, cid in enumerate(p.hand):
        cost = card_cost(cid)
        cost_str = "X" if cost == "X" else ("-" if cost is None else str(cost))
        playable = is_card_playable(p, cid)

        label = f"{idx+1}. {card_name(cid)} (cost {cost_str})"
        row = []
        if playable:
            row.append(
                InlineKeyboardButton(
                    text=f"▶ {label}",
                    callback_data=f"playcard|{game.chat_id}|{p.user_id}|{idx}",
                )
            )
        row.append(
            InlineKeyboardButton(
                text="ℹ️ Info",
                callback_data=f"info|{game.chat_id}|{p.user_id}|{idx}",
            )
        )
        buttons.append(row)

    # Add Done button
    buttons.append([
        InlineKeyboardButton(
            text="✅ Done playing",
            callback_data=f"done|{game.chat_id}|{p.user_id}"
        )
    ])

    text = f"Round {game.round_number}\n{format_hand(p)}\n\nTap ▶ to play cards, ℹ️ for details, then tap Done."

    await context.bot.send_message(
        chat_id=p.user_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def refresh_hand_message(query, context: ContextTypes.DEFAULT_TYPE, game: GameState, p: PlayerState):
    buttons = []
    for idx, cid in enumerate(p.hand):
        cost = card_cost(cid)
        cost_str = "X" if cost == "X" else ("-" if cost is None else str(cost))
        playable = is_card_playable(p, cid)

        label = f"{idx+1}. {card_name(cid)} (cost {cost_str})"
        row = []
        if playable:
            row.append(
                InlineKeyboardButton(
                    text=f"▶ {label}",
                    callback_data=f"playcard|{game.chat_id}|{p.user_id}|{idx}"
                )
            )
        row.append(
            InlineKeyboardButton(
                text="ℹ️ Info",
                callback_data=f"info|{game.chat_id}|{p.user_id}|{idx}",
            )
        )
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            text="✅ Done playing",
            callback_data=f"done|{game.chat_id}|{p.user_id}"
        )
    ])

    text = f"Round {game.round_number}\n{format_hand(p)}\n\nTap ▶ to play cards, ℹ️ for details, then tap Done."
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# =========================
# Card immediate effects
# =========================

def add_curse_to_draw_pile(p: PlayerState, count: int = 1):
    """Add CURSE cards to the player's draw pile (discard, then reshuffle when needed)."""
    for _ in range(max(0, count)):
        p.discard.append("CURSE")


def apply_immediate_effect(game: GameState, p: PlayerState, cid: str, target: Optional[PlayerState], x_value: int):
    """
    Handle the immediate on-play effects that don't wait for /resolve.
    This is intentionally conservative: we implement the common straightforward parts:
      - Draw cards
      - Discard random / specific cards
      - Next-round extra cards / energy
      - Simple block gains
      - Curse insertion
    Complex text (multi-target splits, conditional scaling, etc.) is mostly left for /resolve or future work.
    """
    desc = card_desc(cid).lower()

    # Track that card was played
    p.cards_played_this_round.append(cid)

    # Simple draw effects (very coarse but effective)
    if cid in {
        "QUICK_DRAW", "QUICK_DRAW_UG",
        "SLIM", "SLIM_UG",
        "BATTLE_CRY", "BATTLE_CRY_UG",
        "BALANCE", "BALANCE_UG",
        "CARD_DRAW_2", "CARD_DRAW_2_UG",
        "EXPERT", "EXPERT_UG",
        "GAMBLE", "GAMBLE_UG",
        "BACKPACK", "BACKPACK_UG",
        "OVERLOAD", "OVERLOAD_UG",
        "SCRAPS", "SCRAPS_UG",
        "BRING_IT_ON", "BRING_IT_ON_UG",
        "FLIP", "FLIP_UG",
        "POUND_VOTE", "POUND_VOTE_UG",
        "SLIM", "SLIM_UG",
        "TURBO_TIME", "TURBO_TIME_UG",
        "ESCAPE", "ESCAPE_UG",
    }:
        # Heuristic: look for "draw N cards" patterns.
        # This won't be perfect for every card but covers most.
        if "draw cards until you have 5" in desc:
            # EXPERT
            draw_cards(p, max(0, 5 - len(p.hand)))
        elif "draw cards until you have 6" in desc:
            # EXPERT_UG
            draw_cards(p, max(0, 6 - len(p.hand)))
        elif "draw 4 cards" in desc:
            draw_cards(p, 4)
        elif "draw 3 cards" in desc:
            draw_cards(p, 3)
        elif "draw 2 cards" in desc:
            draw_cards(p, 2)
        elif "draw 1 card" in desc:
            draw_cards(p, 1)

    # Balance / Vote Throw / Backpack discard-then-draw style
    if cid in {"BALANCE", "BALANCE_UG"}:
        # "Draw N cards. Discard 1 card."
        if "draw 3 cards" in desc:
            draw_cards(p, 3)
        elif "draw 4 cards" in desc:
            draw_cards(p, 4)
        if p.hand:
            discard_random(p, 1)

    if cid in {"VOTE_THROW", "VOTE_THROW_UG"}:
        # Draw 1, discard 1
        draw_cards(p, 1)
        if p.hand:
            discard_random(p, 1)

    if cid in {"BACKPACK", "BACKPACK_UG"}:
        # Draw 1, discard 1 (or 2/2)
        if "draw 2 cards" in desc:
            draw_cards(p, 2)
            discard_random(p, min(2, len(p.hand)))
        else:
            draw_cards(p, 1)
            if p.hand:
                discard_random(p, 1)

    if cid in {"GAMBLE", "GAMBLE_UG"}:
        # Discard your hand, then draw that many cards.
        old_count = len(p.hand)
        while p.hand:
            card = p.hand.pop()
            p.discard.append(card)
            p.cards_discarded_this_round.append(card)
        draw_cards(p, old_count)

    # Escape, Bring it On, Flip – add draw + simple blocks logic handled here
    if cid in {"ESCAPE", "ESCAPE_UG"}:
        draw_cards(p, 1)
    if cid in {"BRING_IT_ON", "BRING_IT_ON_UG"}:
        draw_cards(p, 1)
    if cid in {"FLIP", "FLIP_UG"}:
        # Draw extra cards compared to base
        if "draw 3 cards" in desc:
            draw_cards(p, 3)
        else:
            draw_cards(p, 2)

    # Next-round extra card(s)
    if cid in {"GROUP_TALK", "GROUP_TALK_UG"}:
        if "gain +2 card next round" in desc:
            p.next_round_extra_cards += 2
        else:
            p.next_round_extra_cards += 1

    # Next-round energy
    if cid in {"ENERGY_BATTERY", "ENERGY_BATTERY_UG"}:
        p.next_round_energy_bonus += 1

    # Same-round energy gain
    if cid in {"ENERGY_SURGE", "ENERGY_SURGE_UG"}:
        p.energy += 2
    if cid in {"TURBO_TIME", "TURBO_TIME_UG"}:
        # Turbo Time gives immediate energy and adds curses
        if "gain 3e" in desc:
            p.energy += 3
        else:
            p.energy += 2

    # Curses
    if "add a curse card to your draw pile" in desc:
        add_curse_to_draw_pile(p, 1)

    # Simple block effects not fully handled by resolve map
    if cid in {"SURVIVE", "SURVIVE_UG"}:
        # additional block handled via BLOCK_CARDS_SIMPLE in resolve
        # here we only implement the discard 1 card clause
        if p.hand:
            discard_random(p, 1)

    # Trash – very simplified: discard 1 random card and gain 1 energy
    if cid in {"TRASH", "TRASH_UG"}:
        if p.hand:
            discard_random(p, 1)
            p.energy += 1

    # We intentionally leave many of the more complex conditional effects
    # (like "for each curse", "if discarded while scrying", etc.)
    # as future work to keep this engine manageable.


# =========================
# Callback Query Handler
# =========================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = (query.data or "").split("|")

    if not data:
        return

    kind = data[0]

    # ----- Playing cards -----
    if kind == "playcard":
        if len(data) != 4:
            return
        chat_id = int(data[1])
        player_id = int(data[2])
        card_index = int(data[3])

        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return

        p = game.players.get(player_id)
        if not p or not p.alive:
            await query.edit_message_text("You are not in the game or are eliminated.")
            return

        if card_index < 0 or card_index >= len(p.hand):
            await query.edit_message_text("Invalid card selection.")
            return

        cid = p.hand[card_index]
        cost = card_cost(cid)

        # Unplayable cards (curses, etc.)
        if cost is None:
            await query.edit_message_text("That card cannot be played.")
            return

        # Determine energy cost
        if cost == "X":
            if p.energy <= 0:
                await query.edit_message_text("You have no energy left for an X-cost card.")
                return
            energy_spent = p.energy
            x_value = p.energy
        else:
            try:
                c_int = int(cost)
            except Exception:
                c_int = 1
            if p.energy < c_int:
                await query.edit_message_text("Not enough energy for that card.")
                return
            energy_spent = c_int
            x_value = 0

        p.energy -= energy_spent

        # Determine target type
        target_mode = CARD_CATALOG.get(cid, {}).get("target", "other")
        if target_mode in ("self", "none"):
            # Immediately record action: self or no-target
            target_id = player_id if target_mode == "self" else None
            act = Action(source_id=player_id, card_id=cid, target_id=target_id, x_value=x_value)
            game.actions.append(act)

            # Apply immediate (non-vote) effects
            target_player = game.players.get(target_id) if target_id is not None else None
            apply_immediate_effect(game, p, cid, target_player, x_value)

            # After playing, card goes to discard
            p.discard.append(cid)
            del p.hand[card_index]

            await refresh_hand_message(query, context, game, p)
            return

        # Need to pick a target (current engine supports single target only)
        alive = [pl for pl in game.players.values() if pl.alive and pl.user_id != player_id]
        if not alive:
            # no valid target; just discard the card
            act = Action(source_id=player_id, card_id=cid, target_id=None, x_value=x_value)
            game.actions.append(act)
            apply_immediate_effect(game, p, cid, None, x_value)
            p.discard.append(cid)
            del p.hand[card_index]
            await refresh_hand_message(query, context, game, p)
            return

        buttons = []
        for pl in alive:
            buttons.append([
                InlineKeyboardButton(
                    text=pl.username,
                    callback_data=f"target|{chat_id}|{player_id}|{card_index}|{pl.user_id}|{x_value}"
                )
            ])

        await query.edit_message_text(
            f"You selected {card_name(cid)} (spent {energy_spent} energy).\nChoose a target:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif kind == "target":
        if len(data) != 6:
            return
        chat_id = int(data[1])
        player_id = int(data[2])
        card_index = int(data[3])
        target_id = int(data[4])
        x_value = int(data[5])

        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return

        p = game.players.get(player_id)
        t = game.players.get(target_id)
        if not p or not p.alive or not t or not t.alive:
            await query.edit_message_text("Invalid source or target.")
            return

        if card_index < 0 or card_index >= len(p.hand):
            await query.edit_message_text("Invalid card.")
            return

        cid = p.hand[card_index]

        # Special handling for ASSIST_ALLY (delegated vote)
        if cid in {"ASSIST_ALLY", "ASSIST_ALLY_UG"}:
            delegate = t  # the player who will choose where the vote goes

            # Move the card from hand to discard for the giver
            p.discard.append(cid)
            del p.hand[card_index]

            # Build buttons for the delegate to secretly choose a target
            alive_players = [pl for pl in game.players.values() if pl.alive]
            buttons = []
            for pl in alive_players:
                buttons.append([
                    InlineKeyboardButton(
                        text=pl.username,
                        callback_data=(
                            f"assist_target|{chat_id}|{player_id}|{delegate.user_id}|{pl.user_id}|{x_value}|{cid}"
                        ),
                    )
                ])

            # DM the delegate
            try:
                await context.bot.send_message(
                    chat_id=delegate.user_id,
                    text=(
                        f"🤝 {p.username} has given you control of their vote.\n\n"
                        "Choose who this delegated vote should go to:"
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
            except Exception as e:
                logger.error(f"Failed to send assist vote DM to {delegate.user_id}: {e}")
                # If DM fails, the assist is effectively lost

            # Refresh the giver's hand view
            await refresh_hand_message(query, context, game, p)
            return

        # Default behavior for all other targeted cards
        target_player = t
        act = Action(source_id=player_id, card_id=cid, target_id=target_id, x_value=x_value)
        game.actions.append(act)

        # Apply immediate side effects
        apply_immediate_effect(game, p, cid, target_player, x_value)

        p.discard.append(cid)
        del p.hand[card_index]

        await refresh_hand_message(query, context, game, p)

    elif kind == "assist_target":
        # assist_target|chat_id|giver_id|delegate_id|target_id|x_value|cid
        if len(data) != 7:
            return
        chat_id = int(data[1])
        giver_id = int(data[2])
        delegate_id = int(data[3])
        target_id = int(data[4])
        x_value = int(data[5])
        cid = data[6]

        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return

        giver = game.players.get(giver_id)
        delegate = game.players.get(delegate_id)
        target = game.players.get(target_id)

        if not giver or not delegate or not target:
            await query.edit_message_text("One of the players is no longer in the game.")
            return
        if not giver.alive or not delegate.alive or not target.alive:
            await query.edit_message_text("One of the players is no longer alive in the game.")
            return

        # Record the delegated vote as an ASSIST_ALLY action.
        # /resolve already knows how to turn this into +1 or +2 vote(s) on target.
        act = Action(
            source_id=giver_id,
            card_id=cid,
            target_id=target_id,
            x_value=x_value,
        )
        game.actions.append(act)

        await query.edit_message_text(
            f"✅ You directed {giver.username}'s vote to {target.username}."
        )

    elif kind == "done":
        if len(data) != 3:
            return
        chat_id = int(data[1])
        player_id = int(data[2])
        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return
        p = game.players.get(player_id)
        if not p:
            await query.edit_message_text("Player not found.")
            return
        p.turn_done = True
        await query.edit_message_text(
            f"You are done playing this round.\n{format_hand(p)}"
        )

    elif kind == "info":
        # info|chat_id|player_id|card_index
        if len(data) != 4:
            return
        chat_id = int(data[1])
        player_id = int(data[2])
        idx = int(data[3])

        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return
        p = game.players.get(player_id)
        if not p:
            await query.edit_message_text("Player not found.")
            return
        if idx < 0 or idx >= len(p.hand):
            await query.edit_message_text("Card not found.")
            return

        cid = p.hand[idx]
        name = card_name(cid)
        cost = card_cost(cid)
        cost_str = "X" if cost == "X" else ("-" if cost is None else str(cost))
        desc = card_desc(cid)

        playable = is_card_playable(p, cid)

        text = (
            f"📜 *{name}*\n"
            f"Cost: `{cost_str}`\n\n"
            f"{desc}\n\n"
            "Tap ▶ to play it (if you have enough energy), or go back to your hand."
        )

        buttons = []
        if playable:
            buttons.append([
                InlineKeyboardButton(
                    text="▶ Play this card",
                    callback_data=f"playcard|{game.chat_id}|{p.user_id}|{idx}",
                )
            ])
        buttons.append([
            InlineKeyboardButton(
                text="⬅️ Back to hand",
                callback_data=f"backtohand|{game.chat_id}|{p.user_id}",
            )
        ])

        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
        )

    elif kind == "backtohand":
        if len(data) != 3:
            return
        chat_id = int(data[1])
        player_id = int(data[2])
        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return
        p = game.players.get(player_id)
        if not p:
            await query.edit_message_text("Player not found.")
            return
        await refresh_hand_message(query, context, game, p)

    # ----- Reward / draft selection -----
    elif kind == "reward_pick":
        if len(data) != 4:
            return
        chat_id = int(data[1])
        player_id = int(data[2])
        cid = data[3]

        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return

        offers = game.reward_offers.get(player_id, [])
        if cid not in offers:
            await query.edit_message_text("That reward is no longer available.")
            return

        p = game.players.get(player_id)
        if not p:
            await query.edit_message_text("You are not in this game.")
            return

        p.deck.append(cid)
        game.reward_offers[player_id] = []
        p.draft_done = True

        await query.edit_message_text(
            f"✅ You added {card_name(cid)} to your deck."
        )

    elif kind == "reward_skip":
        if len(data) != 3:
            return
        chat_id = int(data[1])
        player_id = int(data[2])

        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return

        game.reward_offers[player_id] = []
        p = game.players.get(player_id)
        if p:
            p.draft_done = True
        await query.edit_message_text("✅ You skipped adding a card to your deck.")

    # ----- Camp (upgrade/remove) -----
    elif kind == "camp_upgrade":
        # camp_upgrade|chat_id|player_id
        if len(data) != 3:
            return
        chat_id = int(data[1])
        player_id = int(data[2])

        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return
        p = game.players.get(player_id)
        if not p or not p.alive:
            await query.edit_message_text("You are no longer in this game.")
            return

        # Only show cards that have an upgraded version
        all_cards = list(set(p.deck + p.discard))
        upgradable = [cid for cid in all_cards if cid in UPGRADE_MAP]

        if not upgradable:
            p.camp_done = True
            await query.edit_message_text("You have no cards that can be upgraded. Camp action complete.")
            return

        buttons = []
        for cid in sorted(upgradable):
            buttons.append([
                InlineKeyboardButton(
                    text=f"Upgrade {card_name(cid)}",
                    callback_data=f"camp_pick_upgrade|{game.chat_id}|{p.user_id}|{cid}",
                )
            ])

        await query.edit_message_text(
            "⬆️ Choose a card to upgrade:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif kind == "camp_remove":
        # camp_remove|chat_id|player_id
        if len(data) != 3:
            return
        chat_id = int(data[1])
        player_id = int(data[2])

        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return
        p = game.players.get(player_id)
        if not p or not p.alive:
            await query.edit_message_text("You are no longer in this game.")
            return

        all_cards = list(set(p.deck + p.discard))
        if not all_cards:
            p.camp_done = True
            await query.edit_message_text("You have no cards to remove. Camp action complete.")
            return

        buttons = []
        for cid in sorted(all_cards):
            buttons.append([
                InlineKeyboardButton(
                    text=f"Remove {card_name(cid)}",
                    callback_data=f"camp_pick_remove|{game.chat_id}|{p.user_id}|{cid}",
                )
            ])

        await query.edit_message_text(
            "🗑 Choose a card to remove from your deck:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif kind == "camp_pick_upgrade":
        # camp_pick_upgrade|chat_id|player_id|card_id
        if len(data) != 4:
            return
        chat_id = int(data[1])
        player_id = int(data[2])
        cid = data[3]

        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return
        p = game.players.get(player_id)
        if not p or not p.alive:
            await query.edit_message_text("You are no longer in this game.")
            return

        new_id = UPGRADE_MAP.get(cid)
        if not new_id:
            await query.answer("This card cannot be upgraded.", show_alert=True)
            return

        upgraded = False
        # Prefer upgrading from deck; if not found, upgrade from discard
        if cid in p.deck:
            idx = p.deck.index(cid)
            p.deck[idx] = new_id
            upgraded = True
        elif cid in p.discard:
            idx = p.discard.index(cid)
            p.discard[idx] = new_id
            upgraded = True

        if not upgraded:
            await query.answer("Card not found in your deck/discard.", show_alert=True)
            return

        p.camp_done = True
        await query.edit_message_text(
            f"✅ Upgraded {card_name(cid)} to {card_name(new_id)}."
        )

    elif kind == "camp_pick_remove":
        # camp_pick_remove|chat_id|player_id|card_id
        if len(data) != 4:
            return
        chat_id = int(data[1])
        player_id = int(data[2])
        cid = data[3]

        game = get_game(chat_id)
        if not game:
            await query.edit_message_text("Game no longer exists.")
            return
        p = game.players.get(player_id)
        if not p or not p.alive:
            await query.edit_message_text("You are no longer in this game.")
            return

        # remove first occurrence in deck, then discard if needed
        removed = False
        if cid in p.deck:
            p.deck.remove(cid)
            removed = True
        elif cid in p.discard:
            p.discard.remove(cid)
            removed = True

        if not removed:
            await query.answer("Card not found in your deck/discard.", show_alert=True)
            return

        p.camp_done = True
        await query.edit_message_text(f"✅ Removed {card_name(cid)} from your deck.")

    else:
        # Unknown callback type
        return


# =========================
# Main – webhook-based (Render-friendly)
# =========================

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env var not set")

    application = ApplicationBuilder().token(token).build()

    # Group commands
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("newgame", newgame))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("startgame", startgame))
    application.add_handler(CommandHandler("nextround", nextround))
    application.add_handler(CommandHandler("resolve", resolve))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("reward", reward))
    application.add_handler(CommandHandler("players", players_cmd))
    application.add_handler(CommandHandler("readycheck", readycheck))
    application.add_handler(CommandHandler("camp", camp))
    application.add_handler(CommandHandler("endgame", endgame))

    # Private commands
    application.add_handler(CommandHandler("start", start_private))
    application.add_handler(CommandHandler("deck", deck_cmd))
    application.add_handler(CommandHandler("remove", remove_cmd))
    application.add_handler(CommandHandler("upgrade", upgrade_cmd))

    # Callback
    application.add_handler(CallbackQueryHandler(handle_callback))

    # --- Webhook config for Render ---
    port = int(os.environ.get("PORT", "10000"))

    # Secret path for webhook (must match Telegram setWebhook and Render URL)
    webhook_path = os.environ.get("WEBHOOK_PATH", "popodoppobbaoxe")

    # Public base URL of your Render service
    base_url = os.environ.get(
        "PUBLIC_URL",
        "https://last-hand-standing-bot-cui9.onrender.com",
    )
    webhook_url = f"{base_url.rstrip('/')}/{webhook_path}"

    logger.info(f"Starting webhook on 0.0.0.0:{port} at path /{webhook_path}")
    logger.info(f"Webhook URL registered with Telegram: {webhook_url}")

    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=webhook_path,
        webhook_url=webhook_url,
    )


if __name__ == "__main__":
    main()
