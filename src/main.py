# forward references are auto resolved
from __future__ import annotations

from abc import ABC, abstractmethod
import random
#from types import SimpleNamespace
from typing import Protocol, Any, Dict, List, Optional, Literal
from enum import Enum
from dataclasses import dataclass


# =============  event types ================

# VALID_ENEMIES = {"goblin", "soldier", "skeleton"}

class EnemyTypes(Enum):
  GOBLIN = 'goblin'
  SOLDIER = 'soldier'
  SKELETON = 'skeleton'
  DRAGON = 'dragon'

@dataclass
class AttackStartedEvent:
  attacker: str
  target: str

@dataclass
class DamageTakenEvent:
  name: str
  damage: int
  remaining_hp: int

@dataclass
class CharacterDied:
  name: str

@dataclass 
class WelcomeEvent:
  game_name: str

# =============  observer pattern ================

class Observer(Protocol):
  def notify(self, event: Any) -> None: pass

class EventBus:
  def __init__(self) -> None:
    self._subscribers: list[Observer] = []

  def subscribe(self, observer: Observer) -> None:
    self._subscribers.append(observer)

  def publish(self, event: Any) -> None:
    for sub in self._subscribers:
      sub.notify(event=event)

# =============  ui ================

class IInput(ABC):
  @abstractmethod
  def read(self, prompt: str) -> str:
    pass

class IOutput(ABC):
  @abstractmethod
  def write(self, text: str) -> None:
    pass

# ============= concrete terminal ui ================

class ConsoleIn(IInput):
  def read(self, prompt: str) -> str:
    return input(prompt).strip().lower()

class ConsoleOut(IOutput):
  def write(self, text: str) -> None:
    print(text)

# ============= all input and output to terminal ================

class ConsoleIOManager:
  """ all input/output messages here """
  def __init__(self, inDevice: IInput, outDevice: IOutput) -> None:
    self.inDevice = inDevice
    self.outDevice = outDevice

  def welcome_message(self, data: WelcomeEvent) -> None:
    self.outDevice.write("\n=========================\n")
    self.outDevice.write(f"Welcome to {data.game_name} Game \n")
    self.outDevice.write("\n=========================\n")

  def take_damage_message(self, data: DamageTakenEvent) -> None:
    """ character takes damage """
    self.outDevice.write(f"{data.name} took {data.damage} damage. remaining HP: {data.remaining_hp}")

  def attack_message(self, data: AttackStartedEvent) -> None:
    self.outDevice.write(f"{data.attacker} attacks: {data.target}")

  def character_died_message(self, data: CharacterDied) -> None:
    self.outDevice.write(f"{data.name} has died!")

# =============  concrete: console io observer ================

class IOObserver(Observer):

  def __init__(self, console_io: ConsoleIOManager) -> None:
    self.console = console_io

  def notify(self, event: Any) -> None:
    
    if isinstance(event, AttackStartedEvent):
      self.console.attack_message(event)
    elif isinstance(event, DamageTakenEvent):
      self.console.take_damage_message(event)
    elif isinstance(event, CharacterDied):
      self.console.character_died_message(event)

    elif isinstance(event, WelcomeEvent):
      self.console.welcome_message(data=event)

# ============= character attack strategies ================

# multiple algorithms for calc attack damage, so we use strategy pattern 
class IAttackStrategy(Protocol):
  def calculate_damage(self, base_attack: int) -> int:
    """ algorithm for calculating attack damage """
    pass

class BasicAttackStrategy(IAttackStrategy):
  def calculate_damage(self, base_attack: int) -> int:
    """ add some basic randomness to attack power """ 
    return base_attack + random.randint(-2, 2)

# ============= character ================

class Character(ABC):
  """ abstract base class for all characters in the Game """

  def __init__(
    self, 
    name: str, 
    stats: 'Stats', 
    io_bus: EventBus,
    attack_strategy: IAttackStrategy,
  ) -> None:
    self.name = name
    self.stats = stats
    self.attack_strategy = attack_strategy

    # io events 
    self.io_bus = io_bus

  @property
  def is_alive(self) -> bool:
    """ check hp, if player alive """
    return self.stats.is_alive()
  
  @property
  def is_dead(self) -> bool:
    """ check if the player is dead, True """
    return self.stats.is_dead()

  def take_damage(self, amount: int) -> None:
    """ reduce HP after defense mitigation """
    damage = max(0, amount - self.stats.defense) # can't be less than 0
    self.stats.hp = self.stats.hp - damage

    #  🔔
    damage_event = DamageTakenEvent(
      damage=damage,
      name=self.name,
      remaining_hp=self.stats.hp
    )
    self.io_bus.publish(event=damage_event)

    # check if character is dead
    if self.stats.is_dead():
      # dead
      self.io_bus.publish(event=CharacterDied(name=self.name))
    
  #@abstractmethod
  def attack_target(self, target: 'Character') -> None:
    """ player can attack """

    # check if player is dead should not be able to attack
    if not self.is_alive: return

    attack_event = AttackStartedEvent(
      attacker=self.name, 
      target=target.name
    )
    self.io_bus.publish(event=attack_event)

    # using some algo to give some randomness to attacks
    damage_amount = self.attack_strategy.calculate_damage(base_attack=self.stats.attack)

    # target takes damage
    target.take_damage(amount=damage_amount)

# ============= stats ================

class Stats:
  def __init__(
      self,
      hp: int,
      attack: int,
      defense: int
  ) -> None:
    self.__hp = hp
    self.__attack = attack
    self.__defense = defense

  @property
  def hp(self) -> int: return self.__hp

  @hp.setter
  def hp(self, value: int) -> None:
    # check if value not smaller then zero
    if value < 0:
      self.__hp = 0
    else:
      self.__hp = value

  @property
  def attack(self) -> int: return self.__attack

  @attack.setter
  def attack(self, value: int) -> None:
    if value < 0:
      raise ValueError("attack must be non-negative")

    self.__attack = value

  @property
  def defense(self) -> int: return self.__defense

  @defense.setter
  def defense(self, value: int) -> None:
    if value < 0:
      raise ValueError('Defense must be non-negative')
    
    self.__defense = value

  # methods
  def is_dead(self) -> bool:
    """ if: dead, return True """
    return self.__hp <= 0

  def is_alive(self) -> bool:
    """ if: alive , return True """
    return self.__hp > 0

    

# ============= Player ================

class Player(Character):
  def __init__(self, name: str, stats: Stats, io_bus: EventBus, attack_strategy: IAttackStrategy) -> None:
    super().__init__(name, stats, io_bus, attack_strategy=attack_strategy)

# ============= Enemy ================

class Enemy(Character):
  def __init__(self, name: str, stats: Stats, io_bus: EventBus, attack_strategy: IAttackStrategy) -> None:
    super().__init__(name, stats, io_bus, attack_strategy=attack_strategy)

# ============= character factory ================

class CharacterFactory:
  @staticmethod
  def create_player(name: str, io_bus: EventBus, attack_strategy: IAttackStrategy) -> Player:
    """ Factory method for creating players """
    stats = Stats(hp=100, attack=10, defense=5)
    return Player(name=name, stats=stats, io_bus=io_bus, attack_strategy=attack_strategy)
  
  @staticmethod
  def create_enemy(enemy_type: EnemyTypes, io_bus: EventBus, attack_strategy: IAttackStrategy) -> Enemy:
    """ Factory method for creating enemies """
    if enemy_type == EnemyTypes.GOBLIN:
      stats = Stats(hp=40, attack=6, defense=3)
      return Enemy(name="Goblin", stats=stats, io_bus=io_bus, attack_strategy=attack_strategy)
    elif enemy_type == EnemyTypes.SOLDIER:
      stats = Stats(hp=60, attack=8, defense=5)
      return Enemy(name="Soldier", stats=stats, io_bus=io_bus, attack_strategy=attack_strategy)
    elif enemy_type == EnemyTypes.SKELETON:
      stats = Stats(hp=30, attack=10, defense=2)
      return Enemy(name="Skeleton", stats=stats, io_bus=io_bus, attack_strategy=attack_strategy)
    elif enemy_type == EnemyTypes.DRAGON:
      stats = Stats(hp=80, attack=20, defense=10)
      return Enemy(name="Dragon", stats=stats, io_bus=io_bus, attack_strategy=attack_strategy)
    else:
      raise ValueError(f"Unknown enemy type: {enemy_type}")


# ============= Game ================

class Game(ABC):
  def __init__(
    self,
    player: Player,
    enemy: Enemy,
    io_bus: EventBus,
  ) -> None:
    self.player = player
    self.enemy = enemy
    self.io_bus = io_bus

  def start(self):
    """ start game flow """

    # welcome message
    self.io_bus.publish(event=WelcomeEvent(game_name="Hot RPG"))

    self.play()

  @abstractmethod
  def play(self):
    """ template method, subclass will implement game loop """
    pass

# ============= game loop ================

class TurnBasedGame(Game):
  """ class without constructor, uses the parent constructor auto """
  def play(self) -> None:
    """ basic turn-based game loop """
    while self.player.is_alive and self.enemy.is_alive:
      self.player_turn()

      self.enemy_turn()

  def player_turn(self) -> None:
    """ player's turn logic """
    self.player.attack_target(target=self.enemy)

  def enemy_turn(self) -> None:
    """ enemy's turn logic """
    self.enemy.attack_target(target=self.player)

# ============= game context ================

class GameContext:
  """ game state manager """

  def __init__(
      self,
      io_bus: EventBus,
      io: ConsoleIOManager,
  ):
    self.io_bus = io_bus
    self.io = io
    self.player: Optional[Player] = None
    self.enemy: Optional[Enemy] = None
    
    # instance of our game -> later: can pause and resume
    self.turn_based_game: Optional[TurnBasedGame] = None
    # current game state, eg: MainMenu or PlayingGame ....
    self.state: Optional[IGameState] = None

    # game outcome
    self.outcome: Optional[Literal['win', 'lose'] | None] = None

  def set_state(self, state: IGameState | None) -> None:
    """ set current game state """
    self.state = state

  def run(self) -> None:
    """ state loop, run as long as state not None -> exitGameState """
    while self.state is not None:
      # run what ever that is ->current state eg: mainMenu etc...
      self.state.run(context=self) # each state.run gets context

# ============= state pattern ================

class IGameState(ABC):
  @abstractmethod
  def run(self, context: GameContext) -> None:
    """ run each state logic """
    pass

# ============= game states ================

class MainMenuState(IGameState):

  def run(self, context: GameContext) -> None:
    """ render main menu, get input and handle choice """

    # render main menu
    context.io.outDevice.write("\n ==== MAIN MENU ====\n")
    context.io.outDevice.write("1. New Game\n")
    context.io.outDevice.write("2. Exit\n")

    # pick and option
    choice = context.io.inDevice.read("choose and option: \n")

    if choice == '1': #start a new game
      context.set_state(CharacterCreationState())
    elif choice == '2': # exit the game
      context.set_state(ExitGameState())
    else:
      context.io.outDevice.write("invalid choice, try again!")
      context.set_state(state=self)# sets MainMenuState again

# ============= character creation state ================

class CharacterCreationState(IGameState):

  def run(self, context: GameContext) -> None:
    """ get user input and create character  """
    # input character name
    name = context.io.inDevice.read("Enter your character's name: \n")

    attack_strategy = BasicAttackStrategy()
    # store the player in global context
    context.player = CharacterFactory.create_player(
      name,
      io_bus=context.io_bus,
      attack_strategy=attack_strategy,
    )

    enemy_type = random.choice(list(EnemyTypes))
    
    context.enemy = CharacterFactory.create_enemy(
      enemy_type=enemy_type,
      io_bus=context.io_bus,
      attack_strategy=attack_strategy,
    )

    # create TurnBasedGame once, store it in context - make:(New Game)
    context.turn_based_game = TurnBasedGame(
      player=context.player,
      enemy=context.enemy,
      io_bus=context.io_bus,
    )

    # set the state to new game
    context.set_state(PlayState())

# ============= new game state ================

class PlayState(IGameState):

  def run(self, context: GameContext) -> None:
    """ run a new game """
    
    # start a new game
    if context.turn_based_game is not None:
      context.turn_based_game.start()
    else:
      context.io.outDevice.write("Error: No game instance found. Returning to main menu.")
      context.set_state(MainMenuState())

    # out of game loop------------here---------------out
    if context.player is not None and context.player.is_alive:
      context.outcome = 'win'
    else: #dead
      context.outcome = 'lose'

    # win or dead => game over
    context.set_state(GameOverState())

# ============= Game over state ================

class GameOverState(IGameState):
  def run(self, context: GameContext) -> None:
    context.io.outDevice.write("\n ==== Game Over ==== \n")

    if context.outcome == 'win':
      context.io.outDevice.write('\n🌟 You won! 🌟\n')
    elif context.outcome == 'lose':
      context.io.outDevice.write('\n💀 You lose! 💀\n')

    context.io.outDevice.write("\n 1. back to main menu \n")
    context.io.outDevice.write("\n 2. Exit \n")
    
    choice = context.io.inDevice.read("choose: > \n")

    if choice == '1':
      context.set_state(MainMenuState())
    else: 
      context.set_state(ExitGameState())


# ============= Exit game state ================

class ExitGameState(IGameState):
  def run(self, context: GameContext) -> None:
    context.io.outDevice.write("Goodbye! \n")
    # set the state to None => to exit the Main loop
    context.set_state(None)
  
# ============= character ================
# ============= character ================
# ============= character ================

def main():
  
  # io event bus
  io_bus = EventBus()

  # print/input to console
  inDevice, outDevice = ConsoleIn(), ConsoleOut()

  # console io manager
  console_io = ConsoleIOManager(
    inDevice=inDevice, 
    outDevice=outDevice
  )
  
  # io observer
  io_observer = IOObserver(console_io=console_io)

  # io observer subscribes to io bus
  io_bus.subscribe(io_observer)

  # context manager
  context: GameContext = GameContext(
    io=console_io,
    io_bus=io_bus
  )

  # set the init state
  context.set_state(MainMenuState())

  # start the Main loop => this is the state loop that controls the menus
  context.run()

# entry point of my app
if __name__ == "__main__":
  main()