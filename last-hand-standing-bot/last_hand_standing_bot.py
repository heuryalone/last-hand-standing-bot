import logging
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
# - rarity: "starter" | "common" | "uncommon"
# - cost: 0, 1, 2, or "X"
# - target: "self", "other", "any", "multi_other", "multi_any", "none"
# - description: rules text (not fully implemented yet)
# NOTE: Only *basic* effects (votes/blocks) are wired into the resolver so far.

CARD_CATALOG: Dict[str, Dict] = {
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
        "description": "Give 1 extra vote to another player.",
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
    "WEAK_BATTERY": {
        "name": "Weak Battery",
        "rarity": "common",
        "cost": 1,
        "target": "self",
        "description": "Next round, start with +0.5 Energy (round up every 2 uses).",
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
    # Buffs for next round etc. (not fully wired yet)
    next_round_extra_cards: int = 0
    next_round_energy_bonus: int = 0
    # For retain-related effects
    retained_last_round: Dict[str, bool] = field(default_factory=dict)


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
    phase: str = "lobby"  # lobby, playing, resolving, finished
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


def card_cost(card_id: str) -> str:
    c = CARD_CATALOG.get(card_id, {}).get("cost", 1)
    return c


def card_has_retain(card_id: str) -> bool:
    desc = CARD_CATALOG.get(card_id, {}).get("description", "").lower()
    return "retain in hand if not played" in desc


def draw_one(player: PlayerState):
    """Draw a single card; reshuffle discard if deck is empty."""
    if not player.deck and player.discard:
        player.deck, player.discard = player.discard, []
        random.shuffle(player.deck)
    if player.deck:
        card = player.deck.pop()
        player.hand.append(card)


def draw_up_to(player: PlayerState, target_hand_size: int):
    while len(player.hand) < target_hand_size:
        # If both deck and discard empty, stop
        if not player.deck and not player.discard:
            break
        draw_one(player)


def format_hand(player: PlayerState) -> str:
    lines = [f"Energy: {player.energy}/{player.energy_max}", "Your hand:"]
    if not player.hand:
        lines.append(" - (empty)")
    else:
        for idx, cid in enumerate(player.hand):
            lines.append(f"{idx+1}. {card_name(cid)} (cost {card_cost(cid)})")
    return "\n".join(lines)


def list_alive_players(game: GameState) -> List[PlayerState]:
    return [p for p in game.players.values() if p.alive]


def list_common_uncommon_ids() -> List[str]:
    ids = []
    for cid, data in CARD_CATALOG.items():
        if data.get("rarity") in ("common", "uncommon"):
            ids.append(cid)
    return ids


# A small, simple mapping of which cards produce votes / blocks for now.
VOTE_CARDS_SIMPLE: Dict[str, int] = {
    "BASE_VOTE": 1,
    "PLUS_ONE_VOTE": 1,
    "POUND_VOTE": 1,
    "PRESSURE_VOTE": 1,
    "DOUBLE_VOTE_2E": 2,
    "DOUBLE_VOTE_SPLIT": 2,
    "BLIND_VOTE": 3,
    "VOTE_THROW": 2,
    "VOTE_SPRAY": 2,
    "CONCENTRATE": 2,
    "RIDDLER": 4,
    "SLASH": 1,
}

BLOCK_CARDS_SIMPLE: Dict[str, int] = {
    "BLOCK_1": 1,
    "SHIELD": 1,
    "BLOCK_2": 2,
    "SURVIVE": 2,
}


# =========================
# Commands: Group
# =========================

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
        "When ready, host can /startgame.",
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

    await update.effective_message.reply_text(
        "🃏 Game started! All players have the starter 10-card deck.\n"
        "Host can now use /nextround to begin Round 1."
    )


@require_game
async def nextround(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    """Start a new round: discard old non-retain cards, reset energy/blocks, draw 3 cards, DM hands."""
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
        f"🔄 Starting Round {game.round_number}! Dealing 3 cards and resetting energy..."
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

        # Store which cards were retained (for "retained from last round" type effects)
        p.retained_last_round = new_retained

        # Reset per-round stats
        p.blocks = 0
        p.votes_cast_this_round = 0
        p.votes_received_this_round = 0

        # Reset energy with bonus if any (Energy Battery etc. not yet wired)
        p.energy_max = 3 + p.next_round_energy_bonus
        p.energy = p.energy_max
        p.next_round_energy_bonus = 0

        # Draw up to 3 + next_round_extra_cards
        target_size = 3 + p.next_round_extra_cards
        p.next_round_extra_cards = 0
        draw_up_to(p, target_size)

        # DM their hand
        try:
            await send_hand_menu(context, game, p)
        except Exception as e:
            logger.error(f"Failed to DM player {p.user_id}: {e}")

    await update.effective_message.reply_text(
        "Hands sent via DM. Players may now play cards until they are done."
    )


@require_game
async def resolve(update: Update, context: ContextTypes.DEFAULT_TYPE, game: GameState):
    """Simple resolver: only basic vote/block effects are implemented so far."""
    user = update.effective_user
    if user.id != game.host_id:
        await update.effective_message.reply_text("Only the host can resolve the round.")
        return

    if not game.actions:
        await update.effective_message.reply_text("No actions were played this round.")
        return

    # Tally plain votes and blocks, based on simplified mapping.
    votes_on: Dict[int, int] = {}
    blocks_on: Dict[int, int] = {}

    for act in game.actions:
        cid = act.card_id
        src = act.source_id
        tgt = act.target_id

        if cid in VOTE_CARDS_SIMPLE and tgt is not None:
            count = VOTE_CARDS_SIMPLE[cid]
            votes_on[tgt] = votes_on.get(tgt, 0) + count
            # track for Walrus etc. later
            game.players[src].votes_cast_this_round += count
            game.players[tgt].votes_received_this_round += count

        if cid in BLOCK_CARDS_SIMPLE:
            # Block always on self for these
            blocks_on[src] = blocks_on.get(src, 0) + BLOCK_CARDS_SIMPLE[cid]

        if cid == "ASSIST_ALLY" and tgt is not None:
            # Give 1 extra vote to another player (counts as a vote)
            votes_on[tgt] = votes_on.get(tgt, 0) + 1

        if cid == "BLOCK_ALLY" and tgt is not None:
            blocks_on[tgt] = blocks_on.get(tgt, 0) + 1

    # Apply blocks: each block cancels 1 vote
    final_votes: Dict[int, int] = {}
    for pid, v in votes_on.items():
        b = blocks_on.get(pid, 0)
        final_votes[pid] = max(0, v - b)

    if not final_votes:
        await update.effective_message.reply_text("After applying blocks, nobody has any votes.")
        return

    # Show results
    lines = ["📊 Round results (basic engine):"]
    for p in list_alive_players(game):
        v = final_votes.get(p.user_id, 0)
        lines.append(f" - {p.username}: {v} vote(s)")
    await update.effective_message.reply_text("\n".join(lines))

    max_votes = max(final_votes.values())
    elim_ids = [pid for pid, v in final_votes.items() if v == max_votes]
    elim_players = [game.players[pid] for pid in elim_ids if game.players[pid].alive]

    if not elim_players:
        await update.effective_message.reply_text("No one is eliminated this round.")
        return

    for p in elim_players:
        p.alive = False

    if len(elim_players) == 1:
        await update.effective_message.reply_text(f"❌ {elim_players[0].username} has been eliminated!")
    else:
        names = ", ".join(p.username for p in elim_players)
        await update.effective_message.reply_text(
            f"❌ Multiple players tied with {max_votes} votes and are eliminated: {names}"
        )

    alive = list_alive_players(game)
    if len(alive) == 1:
        await update.effective_message.reply_text(
            f"🏆 {alive[0].username} is the LAST HAND STANDING! Game over."
        )
        game.phase = "finished"
    elif len(alive) == 0:
        await update.effective_message.reply_text("Everyone has been eliminated. Chaos victory.")
        game.phase = "finished"
    else:
        game.phase = "lobby"
        await update.effective_message.reply_text(
            "Round complete. Host can /nextround to start the next round."
        )


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
    """Host command: send each alive player 3 random Common/Uncommon cards to add or skip."""
    user = update.effective_user
    if user.id != game.host_id:
        await update.effective_message.reply_text("Only the host can grant rewards.")
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

    for p in alive:
        # sample 3 distinct cards (or with replacement if fewer in pool)
        offers = random.sample(pool, k=min(3, len(pool)))
        game.reward_offers[p.user_id] = offers

        buttons = []
        for cid in offers:
            buttons.append([
                InlineKeyboardButton(
                    text=card_name(cid),
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
                    "🎁 Reward! Choose one card to add to your deck or skip:\n\n" +
                    "\n".join(f"- {card_name(cid)}" for cid in offers)
                ),
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        except Exception as e:
            logger.error(f"Failed to send reward DM to {p.user_id}: {e}")

    await update.effective_message.reply_text(
        "Reward choices sent to all alive players via DM."
    )


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
        " /upgrade N – upgrade the Nth card in your deck (placeholder, marks it as upgraded)\n\n"
        "Ask your host to /newgame in a group and then /join."
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
    """Placeholder: upgrade just renames the card ID with _UPG, so you can later define improved cards."""
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
    new_id = f"{old_id}_UPG"

    # If upgraded version isn't defined yet, create a placeholder in catalog.
    if new_id not in CARD_CATALOG:
        base = CARD_CATALOG.get(old_id, {})
        CARD_CATALOG[new_id] = {
            "name": base.get("name", old_id) + " +",
            "rarity": base.get("rarity", "uncommon"),
            "cost": base.get("cost", 1),
            "target": base.get("target", "other"),
            "description": base.get("description", "") + " (Upgraded version – define later.)",
        }

    p.deck[idx] = new_id
    await update.effective_message.reply_text(
        f"Upgraded {card_name(old_id)} to {card_name(new_id)}."
    )


# =========================
# Card play UI (DM)
# =========================

async def send_hand_menu(context: ContextTypes.DEFAULT_TYPE, game: GameState, p: PlayerState):
    """Send or refresh the 'play cards' menu for a player."""
    # Build playable card buttons: cost <= energy (or X-cost if energy>0)
    buttons = []
    for idx, cid in enumerate(p.hand):
        cost = card_cost(cid)
        playable = False
        if cost == "X":
            playable = p.energy > 0
        else:
            try:
                c_int = int(cost)
                playable = p.energy >= c_int
            except Exception:
                playable = False

        text = f"{idx+1}. {card_name(cid)} (cost {cost})"
        if playable:
            buttons.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"playcard|{game.chat_id}|{p.user_id}|{idx}"
                )
            ])

    # Add Done button
    buttons.append([
        InlineKeyboardButton(
            text="✅ Done playing",
            callback_data=f"done|{game.chat_id}|{p.user_id}"
        )
    ])

    text = f"Round {game.round_number}\n{format_hand(p)}\n\nTap cards to play them, then tap Done."

    await context.bot.send_message(
        chat_id=p.user_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def refresh_hand_message(query, context: ContextTypes.DEFAULT_TYPE, game: GameState, p: PlayerState):
    buttons = []
    for idx, cid in enumerate(p.hand):
        cost = card_cost(cid)
        playable = False
        if cost == "X":
            playable = p.energy > 0
        else:
            try:
                c_int = int(cost)
                playable = p.energy >= c_int
            except Exception:
                playable = False

        text = f"{idx+1}. {card_name(cid)} (cost {cost})"
        if playable:
            buttons.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"playcard|{game.chat_id}|{p.user_id}|{idx}"
                )
            ])

    buttons.append([
        InlineKeyboardButton(
            text="✅ Done playing",
            callback_data=f"done|{game.chat_id}|{p.user_id}"
        )
    ])

    text = f"Round {game.round_number}\n{format_hand(p)}\n\nTap cards to play them, then tap Done."
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


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
            # Immediately resolve: self or no-target
            target_id = player_id if target_mode == "self" else None
            act = Action(source_id=player_id, card_id=cid, target_id=target_id, x_value=x_value)
            game.actions.append(act)
            p.discard.append(cid)
            del p.hand[card_index]

            # For now, we do not apply immediate draw/energy/other effects.
            # That will be implemented later as we wire each card.
            await refresh_hand_message(query, context, game, p)
            return

        # Need to pick a target (or multiple). For now, we support single target.
        alive = [pl for pl in game.players.values() if pl.alive and pl.user_id != player_id]
        if not alive:
            # no valid target; just discard the card
            act = Action(source_id=player_id, card_id=cid, target_id=None, x_value=x_value)
            game.actions.append(act)
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
            f"You selected {card_name(cid)} (cost spent {energy_spent}).\nChoose a target:",
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
        act = Action(source_id=player_id, card_id=cid, target_id=target_id, x_value=x_value)
        game.actions.append(act)
        p.discard.append(cid)
        del p.hand[card_index]

        await refresh_hand_message(query, context, game, p)

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
        await query.edit_message_text(
            f"You are done playing this round.\n{format_hand(p)}"
        )

    # ----- Reward selection -----
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

        await query.edit_message_text(
            f"You added {card_name(cid)} to your deck."
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
        await query.edit_message_text("You skipped adding a card to your deck.")


# =========================
# Main
# =========================

def main():
    token = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    app = ApplicationBuilder().token(token).build()

    # Group commands
    app.add_handler(CommandHandler("newgame", newgame))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("startgame", startgame))
    app.add_handler(CommandHandler("nextround", nextround))
    app.add_handler(CommandHandler("resolve", resolve))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("reward", reward))

    # Private commands
    app.add_handler(CommandHandler("start", start_private))
    app.add_handler(CommandHandler("deck", deck_cmd))
    app.add_handler(CommandHandler("remove", remove_cmd))
    app.add_handler(CommandHandler("upgrade", upgrade_cmd))

    # Callback
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
