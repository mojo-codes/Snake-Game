# Snake Game

A enhanced Snake game implementation using Python and Pygame, featuring multiple game modes, rich animations, and sound effects.

## Requirements

- Python 3.x
- Pygame

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. If sound files are missing, the game will automatically create placeholder sounds.

## How to Play

1. Run the game:
```bash
python snake_game.py
```

2. Controls:
- Use arrow keys to control the snake's direction
- Press 'P' to pause/unpause the game
- Press 'R' to reset the game
- Press 'ESC' to return to the main menu
- Close the window to quit

## Game Rules

- Control the snake to eat different types of food:
  - **Cherry (Red)**: Regular food worth 1 point
  - **Pineapple (Yellow)**: Bonus food worth 3 points (appears occasionally and has a time limit)
  - **Avoid Bombs (Purple)**: Game over if you hit them
- The snake grows longer with each food eaten
- Game ends if the snake hits the wall, itself, or a bomb
- Special bomb mechanics:
  - **Simultaneous**: Bomb and food appear at the same time
  - **Sequential**: Bomb appears first, then disappears and food appears in its place

## Game Modes

- **Classic Level**: Original gameplay with no obstacles
- **Obstacles Level**: Includes wall obstacles to navigate around

## Features

### Gameplay
- Multiple game levels (Classic and Obstacles mode)
- Variable food types with different point values
- Bomb mechanics with different strategies
- Snake growth proportional to food value
- Timer bar showing food expiration
- Pause functionality
- High score system with name entry

### Visual Effects
- Animated snake with gradient coloring from head to tail
- Snake eyes that change direction based on movement
- Visual ripple effects when food is consumed
- Pulsating snake body segments after eating
- Pulsating food with sparkle effects
- Particle explosion effects when the snake dies
- Animated game over screen with scaling effects
- Dynamic menu animations
- Timer bar showing remaining time for bonus food

### Audio
- Multiple music themes:
  - **Original**: Classic snake game music - simple and nostalgic
  - **Upbeat**: Energetic music with a faster tempo
  - **Adventure**: Epic soundtrack with sweeping melodies
- Sound effects for eating food, game over, and pausing
- Dynamic music that continues through game over

### User Interface
- Animated main menu with snake icon
- Level selection screen
- Settings menu for music themes
- Detailed game over screen with score display
- High score display and tracking
- Visual hints and instructions

## Development Features
- Modular code structure with separate classes for game elements
- Error handling for music and sound effects
- Automatic generation of placeholder sound files
- Dynamic score animation system

## Credits
- Game developed using Python and Pygame
- Sound effects and music generated procedurally 