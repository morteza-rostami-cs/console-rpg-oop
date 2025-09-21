from __future__ import annotations # class imports fix
"""
# text-based RPG Game: Survive The Dick Land

"""

import random
import json
from abc import ABC, abstractmethod
from typing import Literal, TypedDict, Any, Optional
from dataclasses import dataclass
import time
import uuid
import tkinter as tk
import tkinter.simpledialog as simpledialog
from enum import Enum

#============= tkinter ui ================

class UI:
  """ wrapper around tkinter """

  def __init__(self, root: tk.Tk, context: GameContext) -> None:
    # needs context ->to handle input
    self.context = context

    self.root = root #tkinter root

    self.text_area = tk.Text(root, height=30, width=90, state='disabled')
    self.text_area.pack(pady=10)

    # text-input 
    self.entry = tk.Entry(root, width=100)
    self.entry.pack(pady=5)
    self.entry.bind("<Return>", self.on_submit)

    # some buttons
    self.button_frame = tk.Frame(root)
    self.button_frame.pack(pady=10)

  def read(self, prompt: str) -> str:
    name = simpledialog.askstring(title="Character Creation", prompt=prompt, parent=self.root)

    if name:
      return name
    return 'no input!'

  def close(self) -> None:
    """ close tkinter """
    self.root.after(ms=1000, func=self.root.destroy)

  def display(self, message: str) -> None:
    """ display a message to screen """
    
    self.text_area.config(state='normal')
    self.text_area.insert(tk.END, message + '\n')
    self.text_area.see(tk.END)
    self.text_area.config(state="disabled")

  def on_submit(self, event: Any) -> None: 
    """ capture ui events """
    user_input = self.entry.get()
    self.entry.delete(0, tk.END)

    # handle ui input -> in state.handler_input
    self.context.handle_input(user_input.strip().lower())
  
  def clear_buttons(self) ->None:
    """ clear buttons """
    for widget in self.button_frame.winfo_children():
      widget.destroy()

  def add_button(self, text: str, command: Any) -> None:
    """ add a button with text=button_text, command=callback"""
    button = tk.Button(self.button_frame, text=text, command=command, width=20)
    button.pack(pady=5)

#============= stats ================

@dataclass
class Stats:
  """ encapsulates character stats """
  max_hp: int # maximum health
  attack: int
  defense: int
  current_hp: int | None = None

  # __init__ is auto generated

  def __post_init__(self):
    # if current_hp not set ->set it to max_hp
    if self.current_hp is None:
      self.current_hp = self.max_hp

  def is_alive(self) -> bool:
    """ check if player alive """
    if not self.current_hp:
      raise ValueError("self.current_hp is None")

    return self.current_hp > 0

  def is_dead(self) -> bool:
    """ check if player is dead """
    if not self.current_hp:
      raise ValueError("self.current_hp is None")
    
    return self.current_hp <= 0

  def take_damage(self, dmg: int) -> int:
    """ apply damage after defense mitigation """

    if not self.current_hp: raise ValueError("no self.current_hp")

    net_damage = max(0, dmg - self.defense)
    # apply damage to hp
    self.current_hp = max(0, self.current_hp - net_damage)
    
    return net_damage
  
  def heal(self, amount: int) -> None:
    """ heal but not exceed max_hp """
    if not self.current_hp: raise ValueError("no self.current_hp") 

    self.current_hp = min(self.max_hp, self.current_hp + amount)

#============= enemy types ================

class EnemyTypes(Enum):
  GOBLIN = 'goblin'
  SKELETON = 'skeleton'
  ORC = 'orc'

#============= character ================

class Character(ABC):
  """ abstract base class for all characters """

  def __init__(self, name: str, stats: Stats) -> None:
    self.name = name
    self.stats = stats

  @abstractmethod
  def attack_target(self, target: Character) -> int:
    """ perform an attack on the target , return damage dealt. """
    pass

  def is_alive(self) -> bool:
    return self.stats.is_alive()
  
  def is_dead(self) -> bool:
    return self.stats.is_dead()

#============= player ================

class Player(Character):
  """ the main player """

  def __init__(self, name: str, stats: Stats) -> None:
    super().__init__(name, stats)
    self.inventory: list[str] = []

  def attack_target(self, target: Character) -> int:
    # adding some randomness to our attack
    base_damage = self.stats.attack + random.randint(0, 2)

    dealt = target.stats.take_damage(dmg=base_damage)
    return dealt

#============= enemy ================

class Enemy(Character):
  """ Enemy character with ai """

  def __init__(self, name: str, stats: Stats) -> None:
    super().__init__(name, stats)

  def attack_target(self, target: Character) -> int:
    # some randomness to the enemy damage
    base_damage = self.stats.attack + random.randint(-1, 2)
    # apply the damage
    dealt = target.stats.take_damage(dmg=base_damage)
    return dealt

#============= enemy factory ================

class EnemyFactory:
  """ factory for creating enemies """

  @staticmethod
  def create_enemy(enemy_type: EnemyTypes) -> Enemy:
    if enemy_type == EnemyTypes.GOBLIN:
      return Enemy("Goblin", Stats(max_hp=20, attack=5, defense=1))
    elif enemy_type == EnemyTypes.SKELETON:
      return Enemy("Skeleton", Stats(max_hp=25, attack=6, defense=2))
    elif enemy_type == EnemyTypes.ORC:
      return Enemy("Orc", Stats(max_hp=30, attack=8, defense=3))
    else: 
      raise ValueError(f"unknown enemy type: {enemy_type}")


#============= game state ================

class IGameState(ABC):
  """ interface for all game states """

  @abstractmethod
  def enter(self, context: GameContext) -> None:
    """ runs when entering the state, eg: render initial message """
    pass

  @abstractmethod
  def handle_input(self, context: GameContext, user_input: str) -> None:
    """ pass any input and run each state logic """
    pass

#============= welcome screen state ================

class WelcomeState(IGameState):
  """ welcome screen of the game """

  def enter(self, context: GameContext):
    
    # render welcome screen
    context.ui.display("🌟 Welcome to the RPG Game! 🌟\nPress ENTER to continue...")
    # clear buttons
    context.ui.clear_buttons()

  def handle_input(self, context: GameContext, user_input: str) -> None:
    if user_input == "": # user pressed Enter
      context.ui.display("👉 game continues from here!")
      # main menu
      context.set_state(state=MainMenuState())
    else:
      context.ui.display("❌ Invalid input, please press Enter...")

#============= main menu ================

class MainMenuState(IGameState):
  def enter(self, context: GameContext) -> None:
    context.ui.display("====== Main Menu ======")
    context.ui.display("choose an option \n")

    # clear buttons
    context.ui.clear_buttons()

    # set the buttons -> menu options
    context.ui.add_button("🆕 New Game", lambda: context.set_state(state=CharacterCreationState()))
    context.ui.add_button("🚪 Exit Game", lambda: context.set_state(state=ExitGameState()))

  def handle_input(self, context: GameContext, user_input:str) -> None:
    """ not used: cause we are passing a call back to out button """
    pass

#============= character-creation state ================

class CharacterCreationState(IGameState):
  def enter(self, context: GameContext) -> None:
    """ create player """

    name = context.ui.read(prompt="Enter your name: \n")
    context.ui.display(message=f"Player name: {name}")

    # create a new player
    context.player = Player(
      name=name,
      stats= Stats(max_hp=100, attack=10, defense=9)
    )

    context.set_state(state=NewGameState())

  def handle_input(self, context: GameContext, user_input: str) -> None:
    return super().handle_input(context, user_input)

#============= new game state ================

class NewGameState(IGameState):
  def enter(self, context: GameContext) -> None:

    # create a random enemy
    enemy_types = list(EnemyTypes)
    print(enemy_types)

    enemy_type = random.choice(enemy_types)
    enemy = EnemyFactory.create_enemy(enemy_type=enemy_type)

    context.ui.display(f"⚔️ starting a new adventure... {context.player and context.player.name} - enemy: {enemy.name}")
    context.ui.clear_buttons()
    context.ui.add_button(text="Back to Menu", command=lambda: context.set_state(MainMenuState()))
    context.ui.display("\n=================\n")

  def handle_input(self, context: GameContext, user_input:str) -> None:
    """ not used: cause we are passing a call back to out button """
    pass

#============= Exit game state ================

class ExitGameState(IGameState):
  def enter(self, context: GameContext) -> None:
    """ just clean up on exit """
    context.ui.display(message="\n👋 goodbye! \n")

    # clear buttons
    context.ui.clear_buttons()

    # close window 
    context.ui.close()

    # set the state to None
    context.set_state(state=None)
  
  def handle_input(self, context: GameContext, user_input: str) -> None:
    """ exit state, does not take any input currently """
    return super().handle_input(context, user_input)

#============= game context ================

class GameContext:
  """ hold game state and allows state transition """

  def __init__(
      self, 
      ui: UI,
      ):
    self.ui = ui
    self.player: Optional[Player | None] = None
    self.enemy = None

    # game state
    self.state: IGameState | None = None

  def set_state(self, state: IGameState | None) -> None:
    """ just set the state """
    # set current state
    self.state = state

    # start the program
    self.start()

  def start(self) -> None:
    """ start the current state """
    
    # start the sate flow
    #while self.state: # loop as long as state != None
    if self.state:  
      self.state.enter(context=self)
  
  def handle_input(self, user_input: str) -> None:
    """ on ui submit -> this method will be called """
    if self.state:
      # if state not None -> call state.handle_input
      self.state.handle_input(self, user_input=user_input)


#============= main function ================

def main():
  root = tk.Tk()
  root.title("RPG Game")
  
  # setup context and ui
  context = GameContext(ui=None) # type: ignore

  ui = UI(root=root, context=context)

  # now pass ui back to context
  context.ui = ui

  # set the init state ->and start the game
  context.set_state(WelcomeState())

  # start the game
  #context.start()

  # start the tkinter event_loop
  root.mainloop()

if __name__ == "__main__":
  main()


#============= game state ================
#============= game state ================
#============= game state ================
#============= game state ================
#============= game state ================

