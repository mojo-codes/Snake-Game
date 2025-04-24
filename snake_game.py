import pygame
import random
import sys
import os
import time
import math
from enum import Enum
from highscore import HighscoreManager
import wave
import array
import struct

print("Initializing Pygame...")

# Create essential directories at startup
if not os.path.exists('sounds'):
    print("Creating sounds directory...")
    os.makedirs('sounds')

# Initialize pygame
pygame.init()
print("Initializing Pygame Mixer...")
try:
    pygame.mixer.init(44100, -16, 2, 2048)
    print("Mixer initialized successfully!")
except pygame.error as e:
    print(f"WARNING: Failed to initialize mixer: {e}")
    print("Game will run without sound.")

# Check for sound files
sound_files = [
    'sounds/eat.wav',
    'sounds/game_over.wav',
    'sounds/pause.wav',
    'sounds/background.wav',
    'sounds/background_upbeat.wav',
    'sounds/background_adventure.wav'
]

# Create empty sound files if they don't exist
for sound_file in sound_files:
    if not os.path.exists(sound_file):
        print(f"Creating empty sound file: {sound_file}")
        try:
            # Create a silent WAV file
            with wave.open(sound_file, 'w') as wav_file:
                # Set parameters: 1 channel, 2 bytes per sample, 44100 Hz
                wav_file.setparams((1, 2, 44100, 44100, 'NONE', 'not compressed'))
                wav_file.writeframes(struct.pack('h', 0) * 44100)  # 1 second of silence
        except Exception as e:
            print(f"Error creating sound file {sound_file}: {e}")

# Constants
WINDOW_SIZE = 800
GRID_SIZE = 20
GRID_COUNT = WINDOW_SIZE // GRID_SIZE
FPS = 10
FOOD_TIMER = 10  # Seconds to eat food before game over
BOMB_DURATION = 4  # Seconds that a bomb stays before being replaced with food
PINEAPPLE_DURATION = 3  # Seconds that a pineapple stays before disappearing

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 180, 0)  # Slightly brighter dark green
LIGHT_GREEN = (150, 255, 150)  # Light green for hover
RED = (255, 0, 0)
GRAY = (128, 128, 128)
YELLOW = (255, 255, 0)
PURPLE = (148, 0, 211)  # Brighter purple
DARK_PURPLE = (75, 0, 130)  # Darker purple for contrast
ORANGE = (255, 165, 0)
BLUE = (30, 144, 255)  # Dodger blue for UI elements
WALL_COLOR = (139, 69, 19)  # Brown for walls

# Sound settings
SOUND_VOLUME = 2.5
MUSIC_VOLUME = 2.5

# Game states
class GameState(Enum):
    MENU = 0
    PLAYING = 1
    GAME_OVER = 2
    HIGHSCORE = 3
    LEVEL_SELECT = 4
    SETTINGS = 5

class Level(Enum):
    CLASSIC = 0   # Original level with no obstacles
    OBSTACLES = 1  # Level with wall obstacles

class MusicTheme(Enum):
    ORIGINAL = 0
    UPBEAT = 1
    ADVENTURE = 2

class Direction(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

class FoodType(Enum):
    CHERRY = 1     # Regular food (red cherry) - 1 point
    PINEAPPLE = 2  # Bonus food (yellow pineapple) - 3 points
    BOMB = 3       # Bomb (purple) - game over

class BombStrategy(Enum):
    SIMULTANEOUS = 1  # Bomb and food appear at the same time
    SEQUENTIAL = 2    # Bomb appears first, then disappears and food appears

class ScoreAnimation:
    def __init__(self, score, x, y, color=WHITE):
        self.score = score
        self.x = x
        self.y = y
        self.color = color
        self.alpha = 255  # Full opacity
        self.lifetime = 1.5  # Animation lasts for 1.5 seconds
        self.start_time = time.time()
        self.scale = 1.0  # Added scale factor for pulsing effect
        
    def update(self):
        elapsed = time.time() - self.start_time
        if elapsed > self.lifetime:
            return False  # Animation is done
            
        # Move upward and fade out with pulsing effect
        self.y -= 1.5
        self.alpha = max(0, 255 * (1 - elapsed / self.lifetime))
        # Add pulsing scale effect
        self.scale = 1.0 + 0.3 * math.sin(elapsed * 10)
        return True
        
    def draw(self, surface, font):
        # Create score text with pulsing size effect
        base_font = pygame.font.Font(None, 24)
        pulse_size = int(24 * self.scale)
        pulse_font = pygame.font.Font(None, pulse_size)
        
        score_text = pulse_font.render(f"+{self.score}", True, self.color)
        # Apply transparency
        temp_surface = pygame.Surface(score_text.get_size(), pygame.SRCALPHA)
        temp_surface.fill((0, 0, 0, 0))  # Transparent fill
        temp_surface.blit(score_text, (0, 0))
        temp_surface.set_alpha(int(self.alpha))
        
        # Center the text at the original position regardless of size changes
        x_offset = (score_text.get_width() - base_font.render(f"+{self.score}", True, self.color).get_width()) // 2
        surface.blit(temp_surface, (self.x - x_offset, self.y))

class Snake:
    def __init__(self, level=Level.CLASSIC):
        self.level = level
        self.reset()

    def reset(self):
        self.length = 1
        self.positions = [(GRID_COUNT // 2, GRID_COUNT // 2)]
        self.direction = Direction.RIGHT
        self.score = 0
        self.food_type = None
        self.bomb_strategy = None
        self.bomb_spawn_time = 0
        self.pineapple_spawn_time = 0
        self.bonus_available = False
        self.bonus_timer_start = 0
        self.score_animations = []
        self.game_paused = False  # Track if game was paused
        # Animation effects
        self.growth_segments = []  # Track newly added segments for growth animation
        self.food_eaten_effect = None  # Visual effect when food is eaten
        self.food_eaten_time = 0  # Time when food was eaten
        
        # Initialize wall positions (empty by default for both levels)
        self.wall_positions = []
        # Generate wall obstacles if we're in the obstacle level
        if self.level == Level.OBSTACLES:
            self._generate_walls()
            
        # Generate food after walls are initialized
        self.generate_food()
        self.food_timer = time.time()

    def _generate_walls(self):
        # Clear existing walls
        self.wall_positions = []
        
        # Add some horizontal and vertical walls
        # Make sure walls don't block the entire field and leave enough space for the snake to move
        
        # Vertical wall in the left third of the screen
        wall_x = GRID_COUNT // 3
        for y in range(5, GRID_COUNT - 10):
            # Make a small gap in the middle for passage
            if not (GRID_COUNT // 2 - 2 <= y <= GRID_COUNT // 2 + 2):
                self.wall_positions.append((wall_x, y))
        
        # Vertical wall in right third of the screen
        wall_x = (GRID_COUNT * 2) // 3
        for y in range(10, GRID_COUNT - 5):
            # Make a small gap in the middle for passage
            if not (GRID_COUNT // 2 - 2 <= y <= GRID_COUNT // 2 + 2):
                self.wall_positions.append((wall_x, y))
        
        # Horizontal wall in top third
        wall_y = GRID_COUNT // 3
        for x in range(5, GRID_COUNT - 5):
            # Make gaps for passage
            if not (GRID_COUNT // 3 - 1 <= x <= GRID_COUNT // 3 + 1) and not ((GRID_COUNT * 2) // 3 - 1 <= x <= (GRID_COUNT * 2) // 3 + 1):
                self.wall_positions.append((x, wall_y))
        
        # Horizontal wall in bottom third
        wall_y = (GRID_COUNT * 2) // 3
        for x in range(5, GRID_COUNT - 5):
            # Make gaps for passage
            if not (GRID_COUNT // 3 - 1 <= x <= GRID_COUNT // 3 + 1) and not ((GRID_COUNT * 2) // 3 - 1 <= x <= (GRID_COUNT * 2) // 3 + 1):
                self.wall_positions.append((x, wall_y))
        
        # Add some small wall clusters in the four quadrants
        # Top left quadrant
        for _ in range(3):
            x = random.randint(3, GRID_COUNT // 3 - 3)
            y = random.randint(3, GRID_COUNT // 3 - 3)
            self.wall_positions.append((x, y))
            # Add a small extension
            if random.random() < 0.5:
                self.wall_positions.append((x+1, y))
            else:
                self.wall_positions.append((x, y+1))
                
        # Top right quadrant
        for _ in range(3):
            x = random.randint((GRID_COUNT * 2) // 3 + 3, GRID_COUNT - 3)
            y = random.randint(3, GRID_COUNT // 3 - 3)
            self.wall_positions.append((x, y))
            # Add a small extension
            if random.random() < 0.5:
                self.wall_positions.append((x-1, y))
            else:
                self.wall_positions.append((x, y+1))
                
        # Bottom left quadrant
        for _ in range(3):
            x = random.randint(3, GRID_COUNT // 3 - 3)
            y = random.randint((GRID_COUNT * 2) // 3 + 3, GRID_COUNT - 5)
            self.wall_positions.append((x, y))
            # Add a small extension
            if random.random() < 0.5:
                self.wall_positions.append((x+1, y))
            else:
                self.wall_positions.append((x, y-1))
                
        # Bottom right quadrant
        for _ in range(3):
            x = random.randint((GRID_COUNT * 2) // 3 + 3, GRID_COUNT - 3)
            y = random.randint((GRID_COUNT * 2) // 3 + 3, GRID_COUNT - 5)
            self.wall_positions.append((x, y))
            # Add a small extension
            if random.random() < 0.5:
                self.wall_positions.append((x-1, y))
            else:
                self.wall_positions.append((x, y-1))

    def generate_food(self):
        # Determine food type with probabilities:
        # 75% cherry, 15% pineapple, 10% bomb
        food_type_roll = random.random()
        
        if food_type_roll < 0.75:
            self.food_type = FoodType.CHERRY
            self.bomb = None
            self.bomb_strategy = None
            self.bonus_available = False
            self._generate_regular_food()
        elif food_type_roll < 0.90:  # Increased from 5% to 15% chance
            self.food_type = FoodType.PINEAPPLE
            self.bomb = None
            self.bomb_strategy = None
            self.bonus_available = False
            self._generate_regular_food()
            # Set pineapple spawn time to track when it should disappear
            self.pineapple_spawn_time = time.time()
        else:
            self.food_type = FoodType.BOMB
            
            # Randomly choose between simultaneous and sequential bomb strategies
            if random.random() < 0.5:
                self.bomb_strategy = BombStrategy.SIMULTANEOUS
                self._generate_bomb_with_food()
            else:
                self.bomb_strategy = BombStrategy.SEQUENTIAL
                self._generate_bomb_sequential()
            
        # Reset food timer
        self.food_timer = time.time()

    def _generate_regular_food(self):
        max_attempts = 100  # Avoid infinite loop
        attempts = 0
        
        while attempts < max_attempts:
            # Ensure food doesn't spawn at the bottom where the timer bar is
            food_x = random.randint(0, GRID_COUNT - 1)
            food_y = random.randint(0, GRID_COUNT - 2)  # Avoid bottom row
            self.food = (food_x, food_y)
            
            # Check if food spawned in a valid location
            if (self.food not in self.positions and 
                self.food not in self.wall_positions):
                return True
                
            attempts += 1
            
        # If we couldn't find a valid position after max attempts, try again with less restrictions
        while True:
            food_x = random.randint(0, GRID_COUNT - 1)
            food_y = random.randint(0, GRID_COUNT - 2)  # Avoid bottom row
            self.food = (food_x, food_y)
            if self.food not in self.positions:
                return True

    def _generate_bomb_with_food(self):
        # Strategy 1: Bomb and food appear simultaneously
        max_attempts = 100  # Avoid infinite loop
        attempts = 0
        
        while attempts < max_attempts:
            # Ensure food doesn't spawn at the bottom where the timer bar is
            food_x = random.randint(0, GRID_COUNT - 1)
            food_y = random.randint(0, GRID_COUNT - 2)  # Avoid bottom row
            self.food = (food_x, food_y)
            
            bomb_x = random.randint(0, GRID_COUNT - 1)
            bomb_y = random.randint(0, GRID_COUNT - 2)  # Avoid bottom row
            self.bomb = (bomb_x, bomb_y)
            
            # Make sure bomb and food don't overlap and aren't on the snake or walls
            if (self.bomb != self.food and 
                self.bomb not in self.positions and 
                self.food not in self.positions and
                self.bomb not in self.wall_positions and
                self.food not in self.wall_positions):
                return True
                
            attempts += 1
            
        # If we couldn't find valid positions after max attempts, try again with less restrictions
        while True:
            food_x = random.randint(0, GRID_COUNT - 1)
            food_y = random.randint(0, GRID_COUNT - 2)  # Avoid bottom row
            self.food = (food_x, food_y)
            
            bomb_x = random.randint(0, GRID_COUNT - 1)
            bomb_y = random.randint(0, GRID_COUNT - 2)  # Avoid bottom row
            self.bomb = (bomb_x, bomb_y)
            
            # Make sure bomb and food don't overlap and aren't on the snake
            if (self.bomb != self.food and 
                self.bomb not in self.positions and 
                self.food not in self.positions):
                return True

    def _generate_bomb_sequential(self):
        # Strategy 2: Bomb appears first, then food
        max_attempts = 100  # Avoid infinite loop
        attempts = 0
        
        while attempts < max_attempts:
            bomb_x = random.randint(0, GRID_COUNT - 1)
            bomb_y = random.randint(0, GRID_COUNT - 2)  # Avoid bottom row
            self.bomb = (bomb_x, bomb_y)
            
            if (self.bomb not in self.positions and 
                self.bomb not in self.wall_positions):
                break
                
            attempts += 1
            
        # If too many attempts, try without wall check
        if attempts >= max_attempts:
            while True:
                bomb_x = random.randint(0, GRID_COUNT - 1)
                bomb_y = random.randint(0, GRID_COUNT - 2)  # Avoid bottom row
                self.bomb = (bomb_x, bomb_y)
                
                if self.bomb not in self.positions:
                    break
                
        # Set time when bomb was spawned
        self.bomb_spawn_time = time.time()
        
        # For sequential strategy, we initially have no food
        # Food will be generated after bomb disappears
        self.food = None

    def _replace_bomb_with_food(self):
        # Replace the bomb with a food item
        # Store the bomb position to avoid spawning food right where the bomb was
        old_bomb_pos = self.bomb
        self.bomb = None
        
        # Generate food that's not on the snake or where the bomb was
        max_attempts = 100  # Avoid infinite loop
        attempts = 0
        
        while attempts < max_attempts:
            food_x = random.randint(0, GRID_COUNT - 1)
            food_y = random.randint(0, GRID_COUNT - 2)  # Avoid bottom row
            self.food = (food_x, food_y)
            
            if (self.food not in self.positions and 
                self.food != old_bomb_pos and
                self.food not in self.wall_positions):
                break
                
            attempts += 1
        
        # If too many attempts, try without wall check
        if attempts >= max_attempts:
            while True:
                food_x = random.randint(0, GRID_COUNT - 1)
                food_y = random.randint(0, GRID_COUNT - 2)  # Avoid bottom row
                self.food = (food_x, food_y)
                
                if self.food not in self.positions and self.food != old_bomb_pos:
                    break
                
        # Randomly choose between cherry and pineapple for the replacement food
        if random.random() < 0.7:
            self.food_type = FoodType.CHERRY
        else:
            self.food_type = FoodType.PINEAPPLE
            self.pineapple_spawn_time = time.time()  # Make sure to set the spawn time for pineapple
            
        # Start the bonus timer for fast reaction points
        self.bonus_available = True
        self.bonus_timer_start = time.time()
        
        # FIXED: Don't reset the food timer so player gets remaining time as bonus
        # self.food_timer = time.time()
        
        # Log that we replaced the bomb
        print(f"Replaced bomb with food at {self.food}, type: {self.food_type}")

    def get_head_position(self):
        return self.positions[0]

    def check_bomb_timeout(self):
        # For sequential bomb strategy, check if it's time to replace the bomb with food
        if (self.bomb_strategy == BombStrategy.SEQUENTIAL and 
            self.bomb is not None and 
            time.time() - self.bomb_spawn_time >= BOMB_DURATION):
            
            print("Bomb timeout - replacing with food")
            self._replace_bomb_with_food()
            return True  # Return True if we replaced a bomb
        return False  # Return False if no bomb was replaced

    def check_pineapple_timeout(self):
        # Check if the pineapple has timed out and should disappear
        if (self.food_type == FoodType.PINEAPPLE and 
            time.time() - self.pineapple_spawn_time >= PINEAPPLE_DURATION):
            
            # Replace pineapple with cherry
            self.food_type = FoodType.CHERRY
            self._generate_regular_food()

    def calculate_bonus_points(self):
        if not self.bonus_available:
            return 0
            
        # Calculate how much time is left on the main timer
        elapsed_since_food_timer = time.time() - self.food_timer
        remaining_time = max(0, FOOD_TIMER - elapsed_since_food_timer)
        
        # Convert to an integer for points
        bonus_points = int(remaining_time)
        
        # Give at least 1 bonus point if they were fast enough
        return max(1, bonus_points)

    def update(self):
        # Force check bomb timeout every frame with a definite outcome
        bomb_replaced = self.check_bomb_timeout()
        
        # If there's no food but there is a bomb, make sure the bomb will time out
        if self.food is None and self.bomb is not None:
            current_time = time.time()
            # If bomb has been around for too long, force replacement
            if current_time - self.bomb_spawn_time >= BOMB_DURATION + 1:  # Add 1 second buffer
                print("FORCE BOMB REPLACEMENT - bomb lasted too long")
                self._replace_bomb_with_food()
                bomb_replaced = True
        
        # If there's no food and no bomb, we need to generate food
        if self.food is None and self.bomb is None:
            print("No food and no bomb - generating food")
            self._generate_regular_food()
            # Reset food timer when we manually generate food
            self.food_timer = time.time()
        
        # Check if the pineapple has timed out
        self.check_pineapple_timeout()
        
        # Update food eaten effect if active
        if self.food_eaten_effect:
            if time.time() - self.food_eaten_time > 0.5:  # Effect lasts 0.5 seconds
                self.food_eaten_effect = None
        
        cur = self.get_head_position()
        x, y = cur

        if self.direction == Direction.UP:
            y -= 1
        elif self.direction == Direction.DOWN:
            y += 1
        elif self.direction == Direction.LEFT:
            x -= 1
        elif self.direction == Direction.RIGHT:
            x += 1

        # Check for collisions with walls
        if x < 0 or x >= GRID_COUNT or y < 0 or y >= GRID_COUNT:
            return False

        # Check for collisions with self
        if (x, y) in self.positions[1:]:
            return False
            
        # Check for collisions with wall obstacles (if in obstacle level)
        if (x, y) in self.wall_positions:
            return False
            
        # Check if timer expired and there's no food (special case for sequential bomb strategy)
        if self.food is None and self.bomb_strategy == BombStrategy.SEQUENTIAL:
            # Don't end game if waiting for bomb to be replaced
            if time.time() - self.bomb_spawn_time < BOMB_DURATION:
                # Continue the game while waiting for bomb to time out
                pass
            else:
                # Force the bomb to be replaced with food if it hasn't happened yet
                print("Force replacing bomb with food - sequential strategy")
                self._replace_bomb_with_food()
        # For normal cases, check if timer expired
        elif time.time() - self.food_timer > FOOD_TIMER:
            # Ensure there is food available before failing due to timer
            if self.food is None:
                print("Timer expired but no food available - generating food")
                self._replace_bomb_with_food()
                return True
            # Reset the timer if we somehow missed updating it
            if bomb_replaced:
                print("Timer extension due to bomb replacement")
                self.food_timer = time.time()
                return True
            return False

        self.positions.insert(0, (x, y))
        
        # Age growth segments (reduce intensity of growth animation)
        for i in range(len(self.growth_segments)):
            if self.growth_segments[i] > 0:
                self.growth_segments[i] -= 1

        # Check if food is eaten (and food exists)
        if self.food is not None and (x, y) == self.food:
            # Add growth animation to the head
            self.growth_segments.insert(0, 10)  # Intensity of growth effect (frames)
            
            # Create eating effect animation at food position
            self.food_eaten_effect = self.food
            self.food_eaten_time = time.time()
            
            # Award points based on food type
            food_points = 0
            if self.food_type == FoodType.CHERRY:
                food_points = 1
            elif self.food_type == FoodType.PINEAPPLE:
                food_points = 3
                
            self.score += food_points
            
            # Add bonus points if applicable
            bonus_points = 0
            if self.bonus_available:
                bonus_points = self.calculate_bonus_points()
                if bonus_points > 0:
                    self.score += bonus_points
                    
                    # Create a score animation at the food position
                    screen_x = self.food[0] * GRID_SIZE
                    screen_y = self.food[1] * GRID_SIZE
                    self.score_animations.append(
                        ScoreAnimation(bonus_points, screen_x, screen_y, ORANGE)
                    )
                    
                self.bonus_available = False
                
            # Create a score animation for regular points
            if food_points > 0:
                screen_x = self.food[0] * GRID_SIZE
                screen_y = self.food[1] * GRID_SIZE
                self.score_animations.append(
                    ScoreAnimation(food_points, screen_x, screen_y)
                )
                
            # Generate new food
            self.generate_food()
            return True
            
        # Check if bomb is eaten
        elif self.bomb and (x, y) == self.bomb:
            return False
        else:
            # Ensure growth segments list matches positions list
            if len(self.growth_segments) < len(self.positions):
                self.growth_segments.append(0)
            
            self.positions.pop()
            if len(self.growth_segments) > 0:
                self.growth_segments.pop()
            return True
            
    def update_animations(self):
        # Update and remove finished animations
        self.score_animations = [anim for anim in self.score_animations if anim.update()]

    def draw(self, surface):
        # Draw wall obstacles first (if in obstacle level)
        for wall_pos in self.wall_positions:
            wall_rect = pygame.Rect(
                wall_pos[0] * GRID_SIZE, 
                wall_pos[1] * GRID_SIZE, 
                GRID_SIZE, 
                GRID_SIZE
            )
            # Draw wall with texture
            pygame.draw.rect(surface, WALL_COLOR, wall_rect)
            
            # Add brick pattern
            brick_pattern_color = (160, 82, 45)  # Darker brown for pattern
            # Horizontal lines
            pygame.draw.line(surface, brick_pattern_color, 
                            (wall_pos[0] * GRID_SIZE, wall_pos[1] * GRID_SIZE + GRID_SIZE // 2), 
                            (wall_pos[0] * GRID_SIZE + GRID_SIZE, wall_pos[1] * GRID_SIZE + GRID_SIZE // 2), 1)
            # Vertical lines - offset on alternating rows
            offset = (wall_pos[1] % 2) * (GRID_SIZE // 2)
            pygame.draw.line(surface, brick_pattern_color, 
                            (wall_pos[0] * GRID_SIZE + offset, wall_pos[1] * GRID_SIZE), 
                            (wall_pos[0] * GRID_SIZE + offset, wall_pos[1] * GRID_SIZE + GRID_SIZE), 1)
            
            # Add slight 3D effect with highlights and shadows
            pygame.draw.line(surface, (180, 100, 60), 
                            (wall_pos[0] * GRID_SIZE, wall_pos[1] * GRID_SIZE), 
                            (wall_pos[0] * GRID_SIZE + GRID_SIZE, wall_pos[1] * GRID_SIZE), 1)
            pygame.draw.line(surface, (180, 100, 60), 
                            (wall_pos[0] * GRID_SIZE, wall_pos[1] * GRID_SIZE), 
                            (wall_pos[0] * GRID_SIZE, wall_pos[1] * GRID_SIZE + GRID_SIZE), 1)
            pygame.draw.line(surface, (100, 50, 20), 
                            (wall_pos[0] * GRID_SIZE + GRID_SIZE, wall_pos[1] * GRID_SIZE), 
                            (wall_pos[0] * GRID_SIZE + GRID_SIZE, wall_pos[1] * GRID_SIZE + GRID_SIZE), 1)
            pygame.draw.line(surface, (100, 50, 20), 
                            (wall_pos[0] * GRID_SIZE, wall_pos[1] * GRID_SIZE + GRID_SIZE), 
                            (wall_pos[0] * GRID_SIZE + GRID_SIZE, wall_pos[1] * GRID_SIZE + GRID_SIZE), 1)
                
        # Draw snake with enhanced gradient effect and animations
        for i, p in enumerate(self.positions):
            # Create gradient from bright green (head) to darker green (tail)
            gradient_factor = i / max(1, len(self.positions))
            r = int(DARK_GREEN[0] + (GREEN[0] - DARK_GREEN[0]) * (1 - gradient_factor))
            g = int(DARK_GREEN[1] + (GREEN[1] - DARK_GREEN[1]) * (1 - gradient_factor))
            b = int(DARK_GREEN[2] + (GREEN[2] - DARK_GREEN[2]) * (1 - gradient_factor))
            segment_color = (r, g, b)
            
            # Apply growth effect if this segment is newly added
            growth_effect = 0
            if i < len(self.growth_segments) and self.growth_segments[i] > 0:
                # Make segments pulse when growing
                growth_factor = self.growth_segments[i] / 10
                segment_color = (
                    min(255, r + int(100 * growth_factor)),
                    min(255, g + int(100 * growth_factor)),
                    min(255, b + int(100 * growth_factor))
                )
                growth_effect = int(3 * growth_factor)  # Size increase for growing segments
            
            # Draw each segment with potential growth effect
            rect = pygame.Rect(
                p[0] * GRID_SIZE - growth_effect, 
                p[1] * GRID_SIZE - growth_effect, 
                GRID_SIZE + growth_effect*2, 
                GRID_SIZE + growth_effect*2
            )
            pygame.draw.rect(surface, segment_color, rect, border_radius=growth_effect)
            pygame.draw.rect(surface, BLACK, rect, 1, border_radius=growth_effect)
            
            # Add eye details to head
            if i == 0:  # Head segment
                # Determine eye positions based on direction
                eye_size = GRID_SIZE // 5
                eye_margin = GRID_SIZE // 4
                
                if self.direction == Direction.RIGHT:
                    eye1_pos = (p[0] * GRID_SIZE + GRID_SIZE - eye_margin, p[1] * GRID_SIZE + eye_margin)
                    eye2_pos = (p[0] * GRID_SIZE + GRID_SIZE - eye_margin, p[1] * GRID_SIZE + GRID_SIZE - eye_margin)
                elif self.direction == Direction.LEFT:
                    eye1_pos = (p[0] * GRID_SIZE + eye_margin, p[1] * GRID_SIZE + eye_margin)
                    eye2_pos = (p[0] * GRID_SIZE + eye_margin, p[1] * GRID_SIZE + GRID_SIZE - eye_margin)
                elif self.direction == Direction.UP:
                    eye1_pos = (p[0] * GRID_SIZE + eye_margin, p[1] * GRID_SIZE + eye_margin)
                    eye2_pos = (p[0] * GRID_SIZE + GRID_SIZE - eye_margin, p[1] * GRID_SIZE + eye_margin)
                else:  # DOWN
                    eye1_pos = (p[0] * GRID_SIZE + eye_margin, p[1] * GRID_SIZE + GRID_SIZE - eye_margin)
                    eye2_pos = (p[0] * GRID_SIZE + GRID_SIZE - eye_margin, p[1] * GRID_SIZE + GRID_SIZE - eye_margin)
                    
                pygame.draw.circle(surface, WHITE, eye1_pos, eye_size)
                pygame.draw.circle(surface, WHITE, eye2_pos, eye_size)
                pygame.draw.circle(surface, BLACK, eye1_pos, eye_size // 2)
                pygame.draw.circle(surface, BLACK, eye2_pos, eye_size // 2)

        # Draw food with improved visuals
        if self.food:
            food_x = self.food[0] * GRID_SIZE
            food_y = self.food[1] * GRID_SIZE
            food_center = (food_x + GRID_SIZE // 2, food_y + GRID_SIZE // 2)
            
            if self.food_type == FoodType.CHERRY:
                # Draw cherry with slight bobbing animation
                bob_offset = int(math.sin(time.time() * 5) * 2)
                cherry_radius = GRID_SIZE // 2 - 2
                pygame.draw.circle(surface, RED, (food_x + GRID_SIZE // 3, food_y + GRID_SIZE // 2 + bob_offset), cherry_radius)
                pygame.draw.circle(surface, RED, (food_x + 2 * GRID_SIZE // 3, food_y + GRID_SIZE // 2 + bob_offset), cherry_radius)
                # Draw stem
                stem_start = (food_x + GRID_SIZE // 2, food_y + GRID_SIZE // 3 + bob_offset)
                stem_end = (food_x + GRID_SIZE // 2, food_y + bob_offset)
                pygame.draw.line(surface, DARK_GREEN, stem_start, stem_end, 2)
                
                # Add shine effect
                shine_pos = (food_x + GRID_SIZE // 3 + 2, food_y + GRID_SIZE // 2 + bob_offset - 2)
                pygame.draw.circle(surface, (255, 200, 200), shine_pos, 2)
                
            elif self.food_type == FoodType.PINEAPPLE:
                # Draw pineapple with pulsing animation
                pulse = 1 + 0.1 * math.sin(time.time() * 6)  # Pulsing effect
                pineapple_rect = pygame.Rect(
                    food_x + 2, 
                    food_y + 2, 
                    (GRID_SIZE - 4) * pulse, 
                    (GRID_SIZE - 4) * pulse
                )
                pygame.draw.rect(surface, YELLOW, pineapple_rect, border_radius=3)
                # Add some texture/detail
                for i in range(3):
                    line_y = food_y + (i + 1) * (GRID_SIZE // 4)
                    pygame.draw.line(surface, ORANGE, (food_x + 2, line_y), (food_x + GRID_SIZE - 4, line_y), 1)
                # Add small green leaf on top with movement
                leaf_sway = math.sin(time.time() * 3) * 2
                leaf_points = [
                    (food_x + GRID_SIZE // 2, food_y),
                    (food_x + GRID_SIZE // 2 - 4 + leaf_sway, food_y - 4),
                    (food_x + GRID_SIZE // 2 + 4 + leaf_sway, food_y - 4)
                ]
                pygame.draw.polygon(surface, DARK_GREEN, leaf_points)
                
                # Add sparkle effect that rotates around pineapple
                angle = time.time() * 5
                radius = GRID_SIZE // 2 + 2
                sparkle_x = food_x + GRID_SIZE // 2 + radius * math.cos(angle)
                sparkle_y = food_y + GRID_SIZE // 2 + radius * math.sin(angle)
                pygame.draw.circle(surface, WHITE, (sparkle_x, sparkle_y), 2)
        
        # Draw food eaten effect (expanding circle)
        if self.food_eaten_effect:
            effect_time = time.time() - self.food_eaten_time
            effect_progress = effect_time / 0.5  # 0.5 second animation
            
            if effect_progress <= 1.0:
                effect_x = self.food_eaten_effect[0] * GRID_SIZE + GRID_SIZE // 2
                effect_y = self.food_eaten_effect[1] * GRID_SIZE + GRID_SIZE // 2
                effect_radius = int(GRID_SIZE * 1.5 * effect_progress)
                effect_alpha = int(255 * (1 - effect_progress))
                
                # Create a surface for the effect
                effect_surface = pygame.Surface((effect_radius * 2, effect_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(effect_surface, (255, 255, 255, effect_alpha), (effect_radius, effect_radius), effect_radius)
                
                # Blit the effect surface
                surface.blit(effect_surface, (effect_x - effect_radius, effect_y - effect_radius))
        
        # Draw bomb with improved visuals
        if self.bomb:
            bomb_x = self.bomb[0] * GRID_SIZE
            bomb_y = self.bomb[1] * GRID_SIZE
            bomb_center = (bomb_x + GRID_SIZE // 2, bomb_y + GRID_SIZE // 2)
            
            # Add pulsing effect to bomb
            pulse = 1 + 0.1 * math.sin(time.time() * 8)  # Faster, more urgent pulsing
            bomb_radius = int((GRID_SIZE // 2 - 1) * pulse)
            
            # Draw bomb body
            pygame.draw.circle(surface, DARK_PURPLE, bomb_center, bomb_radius)
            
            # Draw fuse with animated spark
            fuse_start = (bomb_x + GRID_SIZE // 2, bomb_y + GRID_SIZE // 4)
            fuse_curl = math.sin(time.time() * 5) * 3  # Fuse movement
            fuse_end = (bomb_x + GRID_SIZE // 2 + GRID_SIZE // 4 + fuse_curl, bomb_y - 2)
            pygame.draw.line(surface, ORANGE, fuse_start, fuse_end, 2)
            
            # Animate spark on fuse
            spark_size = int(3 + 2 * math.sin(time.time() * 15))  # Flickering spark
            spark_x = fuse_end[0] + int(math.sin(time.time() * 10)) 
            spark_y = fuse_end[1] - 2
            spark_colors = [(255, 255, 0), (255, 200, 0), (255, 150, 0)]  # Yellow to orange
            spark_color = spark_colors[int(time.time() * 10) % len(spark_colors)]
            pygame.draw.circle(surface, spark_color, (spark_x, spark_y), spark_size)
            
            # Add shine effect
            shine_pos = (bomb_x + GRID_SIZE // 3, bomb_y + GRID_SIZE // 3)
            pygame.draw.circle(surface, PURPLE, shine_pos, GRID_SIZE // 8)
        
        # Draw score animations
        font = pygame.font.Font(None, 24)
        for animation in self.score_animations:
            animation.draw(surface, font)
        
    def draw_timer(self, surface):
        # Draw timer bar
        elapsed = time.time() - self.food_timer
        remaining = max(0, FOOD_TIMER - elapsed)
        timer_width = (remaining / FOOD_TIMER) * WINDOW_SIZE
        
        timer_rect = pygame.Rect(0, WINDOW_SIZE - 10, timer_width, 10)
        
        # Change color based on time remaining
        if remaining > FOOD_TIMER * 0.6:
            color = GREEN
        elif remaining > FOOD_TIMER * 0.3:
            color = YELLOW
        else:
            color = RED
            
        pygame.draw.rect(surface, color, timer_rect)
        
        # If we have a bomb with sequential strategy, draw its timer
        if self.bomb_strategy == BombStrategy.SEQUENTIAL and self.bomb is not None:
            bomb_elapsed = time.time() - self.bomb_spawn_time
            bomb_remaining = max(0, BOMB_DURATION - bomb_elapsed)
            bomb_timer_width = (bomb_remaining / BOMB_DURATION) * 100  # 100px wide
            
            bomb_timer_rect = pygame.Rect(WINDOW_SIZE - 110, 40, bomb_timer_width, 6)
            pygame.draw.rect(surface, PURPLE, bomb_timer_rect)
        
        # If we have a pineapple, draw its timer
        if self.food_type == FoodType.PINEAPPLE:
            pineapple_elapsed = time.time() - self.pineapple_spawn_time
            pineapple_remaining = max(0, PINEAPPLE_DURATION - pineapple_elapsed)
            pineapple_timer_width = (pineapple_remaining / PINEAPPLE_DURATION) * 100  # 100px wide
            
            pineapple_timer_rect = pygame.Rect(WINDOW_SIZE - 110, 60, pineapple_timer_width, 6)
            pygame.draw.rect(surface, YELLOW, pineapple_timer_rect)

class Button:
    def __init__(self, text, x, y, width, height, color, hover_color, text_color, icon=None):
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.icon = icon
        self.is_hovered = False
        self.disabled = False
        
    def draw(self, surface, font):
        # Draw button background with rounded corners and gradient effect
        color = GRAY if self.disabled else (self.hover_color if self.is_hovered else self.color)
        
        # Create a surface for the button with alpha for transparency
        button_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Draw main button body with gradient effect
        if not self.disabled:
            for i in range(self.height):
                # Gradient from top to bottom
                gradient_factor = i / self.height
                if self.is_hovered:
                    r = int(color[0] * (1 - gradient_factor * 0.2))
                    g = int(color[1] * (1 - gradient_factor * 0.2))
                    b = int(color[2] * (1 - gradient_factor * 0.2))
                else:
                    r = int(color[0] * (1 - gradient_factor * 0.3))
                    g = int(color[1] * (1 - gradient_factor * 0.3))
                    b = int(color[2] * (1 - gradient_factor * 0.3))
                gradient_color = (r, g, b)
                pygame.draw.line(button_surface, gradient_color, (0, i), (self.width, i))
        else:
            # Fill with gray if disabled
            button_surface.fill(color)
        
        # Draw border
        border_width = 2
        border_color = WHITE
        pygame.draw.rect(button_surface, border_color, pygame.Rect(0, 0, self.width, self.height), border_width, border_radius=10)
        
        # Draw icon if available
        if self.icon:
            icon_size = self.height - 20
            icon_x = 15
            icon_y = (self.height - icon_size) // 2
            
            # Simple icons using pygame shapes with improved aesthetics
            if self.icon == "play":
                # Triangle play icon
                points = [(icon_x, icon_y), 
                          (icon_x, icon_y + icon_size), 
                          (icon_x + icon_size, icon_y + icon_size // 2)]
                pygame.draw.polygon(button_surface, WHITE, points)
                # Add a glow/highlight effect
                highlight_points = [(icon_x+1, icon_y+2), 
                                    (icon_x+1, icon_y + icon_size-2), 
                                    (icon_x + icon_size-2, icon_y + icon_size // 2)]
                pygame.draw.polygon(button_surface, LIGHT_GREEN, highlight_points)
                
            elif self.icon == "trophy":
                # Trophy icon (improved)
                trophy_body = pygame.Rect(icon_x + icon_size//4, icon_y, icon_size//2, icon_size*2//3)
                pygame.draw.rect(button_surface, YELLOW, trophy_body, border_radius=5)
                # Trophy cup
                pygame.draw.arc(button_surface, YELLOW, 
                               (icon_x, icon_y, icon_size, icon_size//2), 
                               3.14, 6.28, 3)
                # Trophy base
                base_rect = pygame.Rect(icon_x + icon_size//6, icon_y + icon_size*2//3, 
                                      icon_size*2//3, icon_size//6)
                pygame.draw.rect(button_surface, YELLOW, base_rect)
                # Trophy stand
                stand_rect = pygame.Rect(icon_x + icon_size//3, icon_y + icon_size*2//3 + icon_size//6, 
                                       icon_size//3, icon_size//6)
                pygame.draw.rect(button_surface, YELLOW, stand_rect)
                
            elif self.icon == "people":
                # Two person icons side by side (improved)
                head_radius = icon_size // 7
                # First person
                pygame.draw.circle(button_surface, WHITE, 
                                  (icon_x + head_radius + 2, icon_y + head_radius + 2), 
                                  head_radius)
                # First person body
                body_points = [
                    (icon_x + head_radius - 2, icon_y + head_radius*2 + 2),
                    (icon_x, icon_y + icon_size),
                    (icon_x + head_radius*2, icon_y + icon_size),
                    (icon_x + head_radius*3 - 2, icon_y + head_radius*2 + 2)
                ]
                pygame.draw.polygon(button_surface, WHITE, body_points)
                
                # Second person (slightly offset)
                pygame.draw.circle(button_surface, WHITE, 
                                  (icon_x + head_radius*3 + 2, icon_y + head_radius), 
                                  head_radius)
                # Second person body
                body_points2 = [
                    (icon_x + head_radius*2 + 2, icon_y + head_radius*2),
                    (icon_x + head_radius*2, icon_y + icon_size),
                    (icon_x + head_radius*4, icon_y + icon_size),
                    (icon_x + head_radius*4 + 2, icon_y + head_radius*2)
                ]
                pygame.draw.polygon(button_surface, WHITE, body_points2)
        
        # Draw text with a subtle shadow effect
        text_color = (180, 180, 180) if self.disabled else self.text_color
        shadow_color = (30, 30, 30, 150)  # Semi-transparent black
        
        # Create text surfaces
        text_surf = font.render(self.text, True, text_color)
        shadow_surf = font.render(self.text, True, shadow_color)
        
        # Position text with shadow effect
        text_x = (self.width - text_surf.get_width()) // 2 + 15 if self.icon else (self.width - text_surf.get_width()) // 2
        text_y = (self.height - text_surf.get_height()) // 2
        
        # Blit shadow slightly offset
        button_surface.blit(shadow_surf, (text_x + 2, text_y + 2))
        # Blit main text
        button_surface.blit(text_surf, (text_x, text_y))
        
        # Blit the button surface to the main surface
        surface.blit(button_surface, (self.x, self.y))
        
    def check_hover(self, mouse_pos):
        if self.disabled:
            self.is_hovered = False
            return False
            
        self.is_hovered = (self.x <= mouse_pos[0] <= self.x + self.width and 
                           self.y <= mouse_pos[1] <= self.y + self.height)
        return self.is_hovered
        
    def is_clicked(self, mouse_pos, mouse_click):
        if self.disabled or not mouse_click:
            return False
            
        return self.check_hover(mouse_pos)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption('Snake Game')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 72)
        self.selected_level = Level.CLASSIC
        self.selected_music_theme = MusicTheme.ORIGINAL
        self.snake = Snake(self.selected_level)
        self.highscore_manager = HighscoreManager()
        self.game_state = GameState.MENU
        self.paused = False
        self.has_active_game = False  # Track if there's a game to continue
        self.player_name = ""
        self.name_input_active = False
        self.last_food_pos = None
        self.sounds_loaded = False
        self.game_over = False  # Add game_over attribute
        
        # Create menu buttons
        self.create_menu_buttons()
        
        self.load_sounds()

    def create_menu_buttons(self):
        button_width, button_height = 240, 50
        center_x = WINDOW_SIZE // 2 - button_width // 2
        
        # Start Game button - always shown
        self.start_button = Button(
            "Start Game", center_x, 240, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, "play"
        )
        
        # Continue button - only shown if there's a paused game
        self.continue_button = Button(
            "Continue Game", center_x, 240, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, "play"
        )
        
        # Level Select button
        self.level_select_button = Button(
            "Level Select", center_x, 310, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, None
        )
        
        # Settings button
        self.settings_button = Button(
            "Settings", center_x, 380, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, None
        )
        
        # Highscore button
        self.highscore_button = Button(
            "Highscore", center_x, 450, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, "trophy"
        )
        
        # Multiplayer button (disabled) - increased width to fit text better
        mult_width = button_width + 80
        self.multiplayer_button = Button(
            "Multiplayer (Coming Soon)", center_x - 40, 520, mult_width, button_height,
            GRAY, GRAY, WHITE, "people"
        )
        
        # Create back button that can be reused across screens
        back_btn_width = 160
        self.top_back_button = Button(
            "Back to Menu", 10, 10, back_btn_width, 40,
            DARK_GREEN, GREEN, WHITE, None
        )
        
        # Level selection buttons (used in level select screen)
        self.classic_level_button = Button(
            "Classic Level", center_x, 240, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, None
        )
        
        self.obstacles_level_button = Button(
            "Obstacle Level", center_x, 310, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, None
        )
        
        self.back_button = Button(
            "Back to Menu", center_x, 500, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, None
        )
        
        # Settings menu buttons
        self.music_orig_button = Button(
            "Original Theme", center_x, 250, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, None
        )
        
        self.music_upbeat_button = Button(
            "Upbeat Theme", center_x, 320, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, None
        )
        
        self.music_adventure_button = Button(
            "Adventure Theme", center_x, 390, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, None
        )
        
        self.settings_back_button = Button(
            "Back to Menu", center_x, 500, button_width, button_height,
            DARK_GREEN, GREEN, WHITE, None
        )

    def load_sounds(self):
        print("\nAttempting to load sound files...")
        try:
            # Check if sound system is working
            if not pygame.mixer.get_init():
                print("Mixer not initialized! Trying to initialize again...")
                pygame.mixer.init(44100, -16, 2, 2048)

            # Print sound file paths and check if they exist
            sound_files = {
                'eat': os.path.join('sounds', 'eat.wav'),
                'game_over': os.path.join('sounds', 'game_over.wav'),
                'pause': os.path.join('sounds', 'pause.wav'),
                'background': os.path.join('sounds', 'background.wav'),
                'background_upbeat': os.path.join('sounds', 'background_upbeat.wav'),
                'background_adventure': os.path.join('sounds', 'background_adventure.wav')
            }

            # Create the sounds directory if it doesn't exist
            if not os.path.exists('sounds'):
                os.makedirs('sounds')
                print("Created sounds directory")

            # Flag to track if we need to generate any music files
            need_to_generate_music = False

            for name, path in sound_files.items():
                print(f"Checking {name} sound file: {path}")
                if not os.path.exists(path):
                    print(f"WARNING: {path} does not exist!")
                    # Mark that we need to generate music files if any background music is missing
                    if name.startswith('background'):
                        need_to_generate_music = True
                else:
                    print(f"Found {path}")

            # Generate all missing music files if needed
            if need_to_generate_music:
                print("Generating missing music files...")
                for name, path in sound_files.items():
                    if name.startswith('background') and not os.path.exists(path):
                        self.generate_placeholder_music(path, name)

            # Load sound effects one by one with error handling
            print("\nLoading sound effects...")
            self.eat_sound = self._load_sound(sound_files['eat'], "eat")
            self.game_over_sound = self._load_sound(sound_files['game_over'], "game over")
            self.pause_sound = self._load_sound(sound_files['pause'], "pause")

            # Set volumes for successfully loaded sounds
            if self.eat_sound:
                self.eat_sound.set_volume(SOUND_VOLUME)
            if self.game_over_sound:
                self.game_over_sound.set_volume(SOUND_VOLUME)
            if self.pause_sound:
                self.pause_sound.set_volume(SOUND_VOLUME)

            # Store music file paths
            self.music_files = {
                MusicTheme.ORIGINAL: sound_files['background'],
                MusicTheme.UPBEAT: sound_files['background_upbeat'],
                MusicTheme.ADVENTURE: sound_files['background_adventure']
            }
            
            # Load and start background music
            print("\nLoading background music...")
            self.background_music_loaded = False
            
            try:
                # Attempt to load the selected theme
                music_path = self.music_files[self.selected_music_theme]
                if os.path.exists(music_path):
                    pygame.mixer.music.load(music_path)
                    pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    pygame.mixer.music.play(-1)  # Loop indefinitely
                    self.background_music_loaded = True
                    print(f"Playing {self.selected_music_theme.name} music theme")
                else:
                    print(f"Warning: Music file {music_path} does not exist.")
                    # Try fallback to another music theme if this one fails
                    self._try_fallback_music()
            except Exception as e:
                print(f"Error loading background music: {e}")
                # Try fallback to another music theme if this one fails
                self._try_fallback_music()

            self.sounds_loaded = True
            print("Sound system initialized!")

        except Exception as e:
            print(f"\nError in sound system: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            self.sounds_loaded = False
            
    def _load_sound(self, path, name):
        """Helper method to load an individual sound file with error handling"""
        try:
            if os.path.exists(path):
                sound = pygame.mixer.Sound(path)
                print(f"{name.capitalize()} sound loaded")
                return sound
            else:
                print(f"Warning: {name} sound file not found at {path}")
                return None
        except Exception as e:
            print(f"Error loading {name} sound: {e}")
            return None
            
    def _try_fallback_music(self):
        """Try to load any available music theme as a fallback"""
        for theme, path in self.music_files.items():
            if theme != self.selected_music_theme and os.path.exists(path):
                try:
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    pygame.mixer.music.play(-1)
                    self.background_music_loaded = True
                    print(f"Fallback: Playing {theme.name} music theme instead")
                    return
                except Exception as e:
                    print(f"Error loading fallback music theme {theme.name}: {e}")
        
        print("Warning: No music themes could be loaded.")

    def generate_placeholder_music(self, filepath, music_type):
        """Generate placeholder music files if they don't exist"""
        try:
            import wave
            import array
            import math
            import random
            
            print(f"Generating placeholder music: {filepath}")
            
            # Create a sounds directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Set parameters
            framerate = 44100
            duration = 30  # seconds
            amplitude = 4000
            num_frames = framerate * duration
            sample_width = 2  # 16-bit
            
            # Create different music patterns based on theme
            data = array.array('h')
            
            if "upbeat" in music_type:
                # Create an upbeat, fast-paced theme with higher notes
                print("Creating upbeat theme...")
                
                # Define some musical parameters
                bpm = 140  # Beats per minute for upbeat theme
                beat_length = 60 / bpm  # Length of one beat in seconds
                
                # Create note sequences for melody
                melodic_pattern = [440, 493.88, 523.25, 587.33, 659.25, 587.33, 523.25, 493.88]
                beat_pattern = [1, 0.5, 0.5, 1, 1, 0.5, 0.5, 1]  # Rhythm pattern
                
                # Generate the music
                position = 0
                
                # Generate simple sine wave melody with clear beats
                while position < num_frames:
                    t = position / framerate
                    
                    # Calculate phase from time for oscillations
                    beat_phase = (t * bpm / 60) % len(beat_pattern)
                    beat_index = int(beat_phase)
                    
                    # Get current note and amplitude from patterns
                    current_note = melodic_pattern[beat_index % len(melodic_pattern)]
                    current_beat = beat_pattern[beat_index % len(beat_pattern)]
                    
                    # Main melody with emphasis on beat
                    melody_val = math.sin(2 * math.pi * current_note * t) * current_beat * 0.8
                    
                    # Add rhythmic percussion on beat
                    drum = 0
                    if beat_phase - beat_index < 0.1:  # At the start of each beat
                        drum = 0.3 * random.uniform(-1, 1)  # Random noise for drum effect
                    
                    # Add bass line (lower octave of melody)
                    bass = 0.4 * math.sin(2 * math.pi * (current_note/2) * t)
                    
                    # Higher harmony notes
                    harmony = 0.2 * math.sin(2 * math.pi * (current_note*1.5) * t)
                    
                    # Calculate sample value
                    sample = amplitude * (melody_val + bass + drum + harmony)
                    data.append(int(sample))
                    position += 1
            
            elif "adventure" in music_type:
                # Create an adventure theme with epic feel
                print("Creating adventure theme...")
                
                # Define musical parameters for adventure theme
                bpm = 90  # Slower for epic feel
                
                # Create chord progression
                chords = [
                    {"notes": [220, 277.18, 329.63], "duration": 4},  # A minor
                    {"notes": [195.99, 246.94, 293.66], "duration": 4},  # G major
                    {"notes": [174.61, 220, 261.63], "duration": 4},  # F major
                    {"notes": [164.81, 196, 246.94], "duration": 4},  # E minor
                ]
                
                # Calculate total progression length in seconds
                progression_length = sum(chord["duration"] for chord in chords) * 60/bpm
                
                position = 0
                
                while position < num_frames:
                    t = position / framerate
                    
                    # Find current position in chord progression
                    cycle_position = t % progression_length
                    current_pos = 0
                    current_chord = chords[0]
                    
                    for chord in chords:
                        chord_duration = chord["duration"] * 60/bpm
                        if current_pos <= cycle_position < current_pos + chord_duration:
                            current_chord = chord
                            break
                        current_pos += chord_duration
                    
                    # Create melody from chord
                    value = 0
                    
                    # Arpeggiate the chord
                    arpeggio_speed = 8  # Notes per second
                    note_index = int(t * arpeggio_speed) % len(current_chord["notes"])
                    current_note = current_chord["notes"][note_index]
                    
                    # Add vibrato to melody
                    vibrato = math.sin(2 * math.pi * 6 * t) * 3
                    melody = 0.6 * math.sin(2 * math.pi * (current_note + vibrato) * t)
                    
                    # Add sustained chord tones for richness
                    chord_tones = 0
                    for i, note in enumerate(current_chord["notes"]):
                        # Vary volumes of different notes
                        volume = 0.2 - (i * 0.05)  # First note loudest
                        chord_tones += volume * math.sin(2 * math.pi * note * t)
                    
                    # Epic sweep effect (slow rising and falling pitch)
                    sweep_speed = 0.2
                    sweep = 0.2 * math.sin(2 * math.pi * sweep_speed * t) * math.sin(2 * math.pi * (current_note/2) * t)
                    
                    # Combine all elements with proper mixing
                    value = melody + chord_tones + sweep
                    sample = int(amplitude * value)
                    data.append(sample)
                    position += 1
            
            else:
                # Original theme with improved melody
                print("Creating original theme...")
                
                # Use pentatonic scale for classic arcade feel
                scale = [261.63, 293.66, 329.63, 392.0, 440.0]  # C D E G A
                
                # Create melody patterns
                main_melody = [0, 2, 4, 2, 3, 1, 0, 0]  # Indexes into scale
                rhythm = [1, 0.5, 0.5, 1, 1, 0.5, 0.5, 1]  # Note durations
                
                bpm = 120
                beats_per_bar = 4
                bar_duration = beats_per_bar * 60/bpm
                melody_duration = len(main_melody) * 60/bpm * 0.5  # Repeat faster
                
                position = 0
                
                while position < num_frames:
                    t = position / framerate
                    
                    # Get current melody note
                    melody_pos = (t % melody_duration) / melody_duration
                    note_idx = int(melody_pos * len(main_melody))
                    scale_idx = main_melody[note_idx]
                    note_freq = scale[scale_idx]
                    
                    # Apply simple envelope
                    note_duration = rhythm[note_idx] * 60/bpm * 0.5
                    note_position = (t % melody_duration) % note_duration
                    envelope = 1.0
                    
                    if note_position < 0.05:  # Attack phase
                        envelope = note_position / 0.05
                    elif note_position > note_duration * 0.7:  # Release phase
                        envelope = 1.0 - ((note_position - note_duration * 0.7) / (note_duration * 0.3))
                    
                    # Main melody
                    melody = envelope * math.sin(2 * math.pi * note_freq * t)
                    
                    # Add bassline
                    bass_note = scale[main_melody[int((t % melody_duration) * 0.5) % len(main_melody)]] / 2
                    bass = 0.3 * math.sin(2 * math.pi * bass_note * t)
                    
                    # Simple rhythm element
                    beat = 0
                    if (t % (60/bpm)) < 0.05:  # Add beat on quarter notes
                        beat = 0.15 * random.uniform(-1, 1)
                    
                    # Combine elements
                    value = 0.6 * melody + 0.3 * bass + 0.1 * beat
                    sample = int(amplitude * value)
                    data.append(sample)
                    position += 1
            
            # Write the WAV file with proper format
            with wave.open(filepath, 'w') as file:
                file.setparams((1, sample_width, framerate, num_frames, 'NONE', 'not compressed'))
                file.writeframes(data.tobytes())
                
            print(f"Successfully created placeholder music: {filepath}")
            
        except Exception as e:
            print(f"Error generating placeholder music: {e}")
            import traceback
            traceback.print_exc()

    def play_music_theme(self, theme):
        """Play the selected music theme"""
        if not self.sounds_loaded:
            print("Warning: Cannot play music theme - sounds not loaded")
            return False
            
        # Stop any currently playing music
        pygame.mixer.music.stop()
        
        # Load and play the selected theme
        try:
            music_path = self.music_files[theme]
            
            # Check if file exists
            if not os.path.exists(music_path):
                print(f"Warning: Music file {music_path} does not exist.")
                # Try to generate the file
                self.generate_placeholder_music(music_path, f"background_{theme.name.lower()}")
                
                # Check again after generation attempt
                if not os.path.exists(music_path):
                    print(f"Error: Could not generate music file {music_path}")
                    return False
            
            # Load and play the music
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play(-1)  # Loop indefinitely
            self.background_music_loaded = True
            self.selected_music_theme = theme
            print(f"Playing {theme.name} music theme")
            return True
        except Exception as e:
            print(f"Error playing music theme: {e}")
            import traceback
            traceback.print_exc()
            return False

    def handle_menu_events(self):
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_click = True
                    
        # Check button interactions
        if self.has_active_game:
            # If we have an active game, show continue instead of start
            if self.continue_button.is_clicked(mouse_pos, mouse_click):
                self.game_state = GameState.PLAYING
                self.paused = False
                # Ensure music continues when returning to a paused game
                if self.background_music_loaded:
                    if not pygame.mixer.music.get_busy():
                        pygame.mixer.music.play(-1)
                    else:
                        pygame.mixer.music.unpause()
        else:
            # Otherwise show start game button
            if self.start_button.is_clicked(mouse_pos, mouse_click):
                self.game_state = GameState.PLAYING
                self.reset_game()
        
        # Level Select button
        if self.level_select_button.is_clicked(mouse_pos, mouse_click):
            self.game_state = GameState.LEVEL_SELECT
            
        # Settings button
        if self.settings_button.is_clicked(mouse_pos, mouse_click):
            self.game_state = GameState.SETTINGS
        
        if self.highscore_button.is_clicked(mouse_pos, mouse_click):
            self.game_state = GameState.HIGHSCORE
        
        # Multiplayer button is disabled, no click handler needed

    def handle_level_select_events(self):
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_click = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game_state = GameState.MENU
        
        # Check button interactions for level selection
        if self.classic_level_button.is_clicked(mouse_pos, mouse_click):
            self.selected_level = Level.CLASSIC
            self.has_active_game = False  # Force new game with new level
            self.game_state = GameState.MENU
            
        if self.obstacles_level_button.is_clicked(mouse_pos, mouse_click):
            self.selected_level = Level.OBSTACLES
            self.has_active_game = False  # Force new game with new level
            self.game_state = GameState.MENU
            
        # Check both back buttons (bottom and top)
        if self.back_button.is_clicked(mouse_pos, mouse_click) or self.top_back_button.is_clicked(mouse_pos, mouse_click):
            print("Back button clicked in level select")
            self.game_state = GameState.MENU

    def handle_settings_events(self):
        """Handle events for the settings screen"""
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_click = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game_state = GameState.MENU
        
        # Original music theme button
        if self.music_orig_button.is_clicked(mouse_pos, mouse_click):
            self.selected_music_theme = MusicTheme.ORIGINAL
            self.play_music_theme(self.selected_music_theme)
            
        # Upbeat music theme button
        if self.music_upbeat_button.is_clicked(mouse_pos, mouse_click):
            self.selected_music_theme = MusicTheme.UPBEAT
            self.play_music_theme(self.selected_music_theme)
            
        # Adventure music theme button
        if self.music_adventure_button.is_clicked(mouse_pos, mouse_click):
            self.selected_music_theme = MusicTheme.ADVENTURE
            self.play_music_theme(self.selected_music_theme)
            
        # Back buttons (both top and bottom)
        if self.settings_back_button.is_clicked(mouse_pos, mouse_click) or self.top_back_button.is_clicked(mouse_pos, mouse_click):
            print("Back button clicked in settings")
            self.game_state = GameState.MENU

    def handle_highscore_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game_state = GameState.MENU

    def handle_game_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p and not self.name_input_active:
                    self.paused = not self.paused
                    if self.sounds_loaded and self.pause_sound:
                        print("Playing pause sound...")
                        self.pause_sound.play()
                    if self.paused and self.background_music_loaded:
                        pygame.mixer.music.pause()
                    elif not self.paused and self.background_music_loaded:
                        pygame.mixer.music.unpause()
                elif event.key == pygame.K_r and not self.name_input_active:
                    self.reset_game()
                elif event.key == pygame.K_ESCAPE:
                    # If we're going back to menu while paused, keep track of active game
                    if self.paused:
                        self.has_active_game = True
                        self.snake.game_paused = True
                    self.game_state = GameState.MENU
                elif not self.paused and self.game_state == GameState.PLAYING:
                    if event.key == pygame.K_UP and self.snake.direction != Direction.DOWN:
                        self.snake.direction = Direction.UP
                    elif event.key == pygame.K_DOWN and self.snake.direction != Direction.UP:
                        self.snake.direction = Direction.DOWN
                    elif event.key == pygame.K_LEFT and self.snake.direction != Direction.RIGHT:
                        self.snake.direction = Direction.LEFT
                    elif event.key == pygame.K_RIGHT and self.snake.direction != Direction.LEFT:
                        self.snake.direction = Direction.RIGHT

    def handle_game_over_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and not self.name_input_active:
                    self.name_input_active = True
                elif event.key == pygame.K_r and not self.name_input_active:
                    self.reset_game()
                    self.game_state = GameState.PLAYING
                elif event.key == pygame.K_ESCAPE:
                    self.has_active_game = False  # Game is over, no active game to continue
                    self.game_state = GameState.MENU
                elif self.name_input_active:
                    if event.key == pygame.K_RETURN and self.player_name:
                        self.highscore_manager.add_score(self.player_name, self.snake.score)
                        self.name_input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        self.player_name = self.player_name[:-1]
                    elif event.unicode.isalnum() or event.unicode.isspace():
                        self.player_name += event.unicode

    def reset_game(self):
        # Reset game state
        self.snake = Snake(self.selected_level)
        self.paused = False
        self.game_over = False  # Reset game_over flag
        self.game_over_explosion_particles = []
        
        # Only try to play music if it's loaded
        try:
            # Check if music is loaded before playing
            if pygame.mixer.music.get_busy() or pygame.mixer.music.get_pos() >= 0:
                pygame.mixer.music.stop()
                pygame.mixer.music.play(-1)
            else:
                # Try to load and play the selected theme
                self.play_music_theme(self.selected_music_theme)
        except pygame.error:
            print("Warning: Unable to play music. Music may not be loaded properly.")

    def draw_score(self):
        score_text = self.font.render(f'Score: {self.snake.score}', True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        # Draw food timer info
        elapsed = time.time() - self.snake.food_timer
        remaining = max(0, FOOD_TIMER - elapsed)
        timer_text = self.small_font.render(f'Time: {remaining:.1f}s', True, WHITE)
        self.screen.blit(timer_text, (WINDOW_SIZE - 120, 10))
        
        # Draw food type info - fixed the potential crash by always setting food_text
        if self.snake.food_type == FoodType.CHERRY:
            food_text = self.small_font.render('Food: Cherry (1 pt)', True, RED)
        elif self.snake.food_type == FoodType.PINEAPPLE:
            pineapple_elapsed = time.time() - self.snake.pineapple_spawn_time
            pineapple_remaining = max(0, PINEAPPLE_DURATION - pineapple_elapsed)
            food_text = self.small_font.render(f'Pineapple: 3 pts ({pineapple_remaining:.1f}s)', True, YELLOW)
        elif self.snake.food_type == FoodType.BOMB:
            # Show different text based on bomb strategy
            if self.snake.bomb_strategy == BombStrategy.SIMULTANEOUS:
                food_text = self.small_font.render('Danger: Avoid Bomb!', True, PURPLE)
            else:
                if self.snake.bomb:
                    bomb_elapsed = time.time() - self.snake.bomb_spawn_time
                    bomb_remaining = max(0, BOMB_DURATION - bomb_elapsed)
                    food_text = self.small_font.render(f'Bomb disappears in: {bomb_remaining:.1f}s', True, PURPLE)
                else:
                    # Bomb has been replaced with food
                    food_text = self.small_font.render('Quick! Bonus points available!', True, ORANGE)
        else:
            food_text = self.small_font.render('Food: Unknown', True, WHITE)
        
        self.screen.blit(food_text, (WINDOW_SIZE // 2 - 120, 10))
        
        # If bomb exists and using simultaneous strategy, display warning
        if self.snake.bomb and self.snake.bomb_strategy == BombStrategy.SIMULTANEOUS:
            bomb_text = self.small_font.render('WARNING: Bomb!', True, PURPLE)
            self.screen.blit(bomb_text, (WINDOW_SIZE // 2 - 70, 40))

    def draw_menu(self):
        # Draw animated background with subtle pattern
        self.screen.fill(BLACK)
        
        # Draw grid pattern for background
        for x in range(0, WINDOW_SIZE, GRID_SIZE*2):
            for y in range(0, WINDOW_SIZE, GRID_SIZE*2):
                # Use a time-based animation for subtle movement
                offset = int(math.sin(time.time() * 1.5) * 3)
                rect = pygame.Rect(x + offset, y, GRID_SIZE, GRID_SIZE)
                pygame.draw.rect(self.screen, (0, 50, 0), rect)  # Very dark green
        
        # Create a semi-transparent overlay for the center menu area
        overlay = pygame.Surface((WINDOW_SIZE - 100, WINDOW_SIZE - 150), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        self.screen.blit(overlay, (50, 75))
        
        # Draw animated snake elements around the border
        num_segments = 20
        for i in range(num_segments):
            # Calculate position around the border
            angle = (i / num_segments * 2 * math.pi) + (time.time() * 0.5)
            radius = min(WINDOW_SIZE // 2 - 20, WINDOW_SIZE // 2 - 20)
            x = WINDOW_SIZE // 2 + radius * math.cos(angle)
            y = WINDOW_SIZE // 2 + radius * math.sin(angle)
            
            # Draw snake segment
            segment_color = (
                int(0),
                int(180 + 75 * math.sin(i / num_segments * math.pi + time.time())),
                int(0)
            )
            pygame.draw.circle(self.screen, segment_color, (int(x), int(y)), 8)
        
        # Draw title with glow effect
        title_text = self.large_font.render('SNAKE GAME', True, GREEN)
        # Create glow by drawing multiple versions with increasing transparency
        for i in range(10, 0, -2):
            glow_surface = pygame.Surface((title_text.get_width() + i*4, title_text.get_height() + i*4), pygame.SRCALPHA)
            glow_color = (0, 255, 0, 5)  # Very transparent green
            pygame.draw.rect(glow_surface, glow_color, glow_surface.get_rect(), border_radius=i*2)
            self.screen.blit(glow_surface, (WINDOW_SIZE//2 - title_text.get_width()//2 - i*2, 150 - i*2))
        
        # Main title
        title_rect = title_text.get_rect(center=(WINDOW_SIZE//2, 150))
        self.screen.blit(title_text, title_rect)
        
        # Draw subtitle with a subtle animation
        subtitle_color = (255, 255, 255, int(127 + 127 * math.sin(time.time() * 2)))
        subtitle_surface = pygame.Surface((300, 40), pygame.SRCALPHA)
        subtitle_text = self.font.render('Select an option:', True, subtitle_color)
        subtitle_rect = subtitle_text.get_rect(center=(300//2, 40//2))
        subtitle_surface.blit(subtitle_text, subtitle_rect)
        self.screen.blit(subtitle_surface, (WINDOW_SIZE//2 - 150, 200))
        
        # Update button hover states
        if self.has_active_game:
            self.continue_button.check_hover(pygame.mouse.get_pos())
        else:
            self.start_button.check_hover(pygame.mouse.get_pos())
        
        self.level_select_button.check_hover(pygame.mouse.get_pos())
        self.settings_button.check_hover(pygame.mouse.get_pos())
        self.highscore_button.check_hover(pygame.mouse.get_pos())
        self.multiplayer_button.check_hover(pygame.mouse.get_pos())
        
        # Set multiplayer button as disabled
        self.multiplayer_button.disabled = True
        
        # Draw buttons
        if self.has_active_game:
            self.continue_button.draw(self.screen, self.font)
        else:
            self.start_button.draw(self.screen, self.font)
        
        self.level_select_button.draw(self.screen, self.font)
        self.settings_button.draw(self.screen, self.font)
        self.highscore_button.draw(self.screen, self.font)
        self.multiplayer_button.draw(self.screen, self.font)
        
        # Show current selected level and music theme
        level_text = f"Current Level: {self.selected_level.name.capitalize()}"
        level_surface = self.small_font.render(level_text, True, LIGHT_GREEN)
        level_rect = level_surface.get_rect(center=(WINDOW_SIZE // 2, 580))
        self.screen.blit(level_surface, level_rect)
        
        music_text = f"Music Theme: {self.selected_music_theme.name.capitalize()}"
        music_surface = self.small_font.render(music_text, True, LIGHT_GREEN)
        music_rect = music_surface.get_rect(center=(WINDOW_SIZE // 2, 600))
        self.screen.blit(music_surface, music_rect)
        
        # Draw instructions with styled box (moved to avoid overlap with buttons)
        instruction_box = pygame.Surface((WINDOW_SIZE - 140, 140), pygame.SRCALPHA)
        instruction_box.fill((0, 50, 0, 100))  # Semi-transparent dark green
        pygame.draw.rect(instruction_box, (0, 100, 0, 150), instruction_box.get_rect(), 2, border_radius=10)
        self.screen.blit(instruction_box, (70, 630))
        
        # Fix layout of instructions - simplified single-column layout
        instructions = [
            "How to Play:",
            "Use arrow keys to move",
            "Eat food to grow and score points",
            "Cherry: 1 point",
            "Pineapple: 3 points (disappears after 3 seconds)",
            "Avoid bombs and don't hit yourself",
            "Eat each food within 10 seconds"
        ]
        
        # Draw instructions with proper spacing and no text cutoff
        y_pos = 640
        for i, instruction in enumerate(instructions):
            # Add icons for different instruction types
            if i == 0:  # Title
                text = self.small_font.render(instruction, True, LIGHT_GREEN)
                self.screen.blit(text, (WINDOW_SIZE//2 - text.get_width()//2, y_pos))
                y_pos += 20
            else:
                if "Cherry" in instruction:
                    icon_color = RED
                elif "Pineapple" in instruction:
                    icon_color = YELLOW
                elif "Avoid bombs" in instruction:
                    icon_color = PURPLE
                else:
                    icon_color = WHITE
                    
                # Draw dot before instruction
                pygame.draw.circle(self.screen, icon_color, (100, y_pos + 7), 4)
                
                # Simple left-aligned text that won't get cut off
                text = self.small_font.render(instruction, True, WHITE)
                self.screen.blit(text, (120, y_pos))
                y_pos += 20

    def draw_level_select_screen(self):
        # Draw animated background
        self.screen.fill(BLACK)
        
        # Draw grid pattern for background
        for x in range(0, WINDOW_SIZE, GRID_SIZE*2):
            for y in range(0, WINDOW_SIZE, GRID_SIZE*2):
                offset = int(math.sin(time.time() * 1.5) * 3)
                rect = pygame.Rect(x + offset, y, GRID_SIZE, GRID_SIZE)
                pygame.draw.rect(self.screen, (0, 50, 0), rect)  # Very dark green
        
        # Create a semi-transparent overlay
        overlay = pygame.Surface((WINDOW_SIZE - 100, WINDOW_SIZE - 150), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        self.screen.blit(overlay, (50, 75))
        
        # Draw title
        title_text = self.large_font.render('SELECT LEVEL', True, GREEN)
        title_rect = title_text.get_rect(center=(WINDOW_SIZE//2, 150))
        self.screen.blit(title_text, title_rect)
        
        # Update button hover states
        self.classic_level_button.check_hover(pygame.mouse.get_pos())
        self.obstacles_level_button.check_hover(pygame.mouse.get_pos())
        self.back_button.check_hover(pygame.mouse.get_pos())
        self.top_back_button.check_hover(pygame.mouse.get_pos())
        
        # Mark the currently selected level button
        if self.selected_level == Level.CLASSIC:
            self.classic_level_button.color = GREEN
            self.obstacles_level_button.color = DARK_GREEN
        else:
            self.classic_level_button.color = DARK_GREEN
            self.obstacles_level_button.color = GREEN
        
        # Draw buttons
        self.classic_level_button.draw(self.screen, self.font)
        self.obstacles_level_button.draw(self.screen, self.font)
        self.back_button.draw(self.screen, self.font)
        
        # Draw additional back button in top-left corner
        self.top_back_button.draw(self.screen, self.small_font)
        
        # Add ESC hint
        esc_hint = self.small_font.render("Press ESC to return to Menu", True, WHITE)
        self.screen.blit(esc_hint, (WINDOW_SIZE//2 - esc_hint.get_width()//2, 550))
        
        # Improved layout for level descriptions
        level_descriptions = [
            {
                "title": "Classic Level:", 
                "desc": "The original Snake game with no obstacles.",
                "y_pos": 380
            },
            {
                "title": "Obstacle Level:", 
                "desc": "Navigate around wall obstacles for an extra challenge!",
                "y_pos": 480
            }
        ]
        
        # Draw each level description with preview in separate areas
        for i, desc in enumerate(level_descriptions):
            # Draw container
            container_height = 80
            container = pygame.Rect(WINDOW_SIZE//2 - 280, desc["y_pos"], 560, container_height)
            is_selected = (i == self.selected_level.value)
            
            # Different appearance for selected level
            pygame.draw.rect(self.screen, (0, 60, 0) if is_selected else (0, 40, 0), container)
            pygame.draw.rect(self.screen, GREEN if is_selected else DARK_GREEN, container, 2, border_radius=5)
            
            # Draw level info on the left side (60% of width)
            text_area_width = 320
            
            # Draw title and description in the text area
            title_surface = self.font.render(desc["title"], True, WHITE)
            desc_surface = self.small_font.render(desc["desc"], True, LIGHT_GREEN)
            
            # Position text
            self.screen.blit(title_surface, (WINDOW_SIZE//2 - 250, desc["y_pos"] + 15))
            self.screen.blit(desc_surface, (WINDOW_SIZE//2 - 250, desc["y_pos"] + 45))
            
            # Draw vertical separator
            separator_x = WINDOW_SIZE//2 - 280 + text_area_width
            pygame.draw.line(self.screen, DARK_GREEN, 
                           (separator_x, desc["y_pos"] + 10), 
                           (separator_x, desc["y_pos"] + container_height - 10), 1)
            
            # Draw visual preview on the right side (remaining 40% of width)
            preview_area = pygame.Rect(
                separator_x + 10, 
                desc["y_pos"] + 10, 
                560 - text_area_width - 20, 
                container_height - 20
            )
            pygame.draw.rect(self.screen, (0, 30, 0), preview_area)
            
            # Draw level-specific visualization in the preview area
            if i == 0:  # Classic level
                # Draw simple snake path
                snake_x_start = preview_area.x + 10
                snake_y = preview_area.y + preview_area.height // 2
                for j in range(5):
                    pygame.draw.rect(self.screen, GREEN, 
                                   (snake_x_start + j*12, snake_y, 10, 10))
                # Draw food
                pygame.draw.circle(self.screen, RED, 
                                 (preview_area.x + preview_area.width - 20, snake_y), 5)
            else:  # Obstacle level
                # Draw a miniature obstacle course 
                # Vertical walls
                wall_x1 = preview_area.x + preview_area.width // 4
                wall_x2 = preview_area.x + (preview_area.width * 3) // 4
                
                for j in range(3):
                    y_pos = preview_area.y + 10 + j*15
                    # Draw walls
                    pygame.draw.rect(self.screen, WALL_COLOR, 
                                   (wall_x1, y_pos, 8, 10))
                    pygame.draw.rect(self.screen, WALL_COLOR, 
                                   (wall_x2, y_pos, 8, 10))
                
                # Draw snake navigating between obstacles 
                snake_y = preview_area.y + preview_area.height - 15
                for j in range(4):
                    pygame.draw.rect(self.screen, GREEN, 
                                   (preview_area.x + 15 + j*12, snake_y, 10, 10))

    def draw_highscore_screen(self):
        self.screen.fill(BLACK)
        
        # Draw title
        title_text = self.large_font.render('HIGHSCORES', True, YELLOW)
        title_rect = title_text.get_rect(center=(WINDOW_SIZE//2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Draw highscores
        highscores = self.highscore_manager.get_highscores()
        if highscores:
            y_offset = 180
            for i, score in enumerate(highscores[:10]):
                score_text = self.font.render(f"{i+1}. {score['name']}: {score['score']}", True, WHITE)
                score_rect = score_text.get_rect(center=(WINDOW_SIZE//2, y_offset))
                self.screen.blit(score_text, score_rect)
                y_offset += 40
        else:
            no_scores_text = self.font.render("No highscores yet!", True, WHITE)
            no_scores_rect = no_scores_text.get_rect(center=(WINDOW_SIZE//2, 250))
            self.screen.blit(no_scores_text, no_scores_rect)
        
        # Draw back instruction
        back_text = self.small_font.render("Press ESC to return to menu", True, WHITE)
        back_rect = back_text.get_rect(center=(WINDOW_SIZE//2, WINDOW_SIZE - 50))
        self.screen.blit(back_text, back_rect)

    def draw_pause_screen(self):
        s = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        s.fill((0, 0, 0, 128))
        self.screen.blit(s, (0, 0))
        pause_text = self.font.render('PAUSED', True, WHITE)
        text_rect = pause_text.get_rect(center=(WINDOW_SIZE/2, WINDOW_SIZE/2))
        self.screen.blit(pause_text, text_rect)
        continue_text = self.small_font.render('Press P to continue', True, WHITE)
        continue_rect = continue_text.get_rect(center=(WINDOW_SIZE/2, WINDOW_SIZE/2 + 40))
        self.screen.blit(continue_text, continue_rect)
        menu_text = self.small_font.render('Press ESC for menu', True, WHITE)
        menu_rect = menu_text.get_rect(center=(WINDOW_SIZE/2, WINDOW_SIZE/2 + 70))
        self.screen.blit(menu_text, menu_rect)

    def draw_game_over_screen(self):
        s = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))  # Slightly more transparent for better effect
        self.screen.blit(s, (0, 0))
        
        # Create a dramatic pulsing red border
        border_thickness = 5 + int(3 * math.sin(time.time() * 5))
        border_rect = pygame.Rect(border_thickness, border_thickness, 
                                 WINDOW_SIZE - border_thickness*2, 
                                 WINDOW_SIZE - border_thickness*2)
        pygame.draw.rect(self.screen, RED, border_rect, border_thickness, border_radius=10)
        
        if not self.name_input_active:
            # Draw animated game over text with shaking effect
            shake_x = int(math.sin(time.time() * 15) * 3)
            shake_y = int(math.cos(time.time() * 12) * 2)
            
            # Create larger text with glow effect
            game_over_text = self.large_font.render('GAME OVER', True, RED)
            text_rect = game_over_text.get_rect(center=(WINDOW_SIZE/2 + shake_x, WINDOW_SIZE/2 - 80 + shake_y))
            
            # Add glow effect to text
            for offset in range(8, 0, -2):
                glow_surface = pygame.Surface((game_over_text.get_width() + offset*2, 
                                              game_over_text.get_height() + offset*2), 
                                              pygame.SRCALPHA)
                glow_color = (255, 0, 0, 5 + offset*2)  # Red glow with increasing opacity
                glow_rect = pygame.Rect(offset, offset, 
                                      game_over_text.get_width(), 
                                      game_over_text.get_height())
                pygame.draw.rect(glow_surface, glow_color, glow_rect, border_radius=offset)
                glow_rect = glow_surface.get_rect(center=(WINDOW_SIZE/2 + shake_x, WINDOW_SIZE/2 - 80 + shake_y))
                self.screen.blit(glow_surface, glow_rect)
            
            self.screen.blit(game_over_text, text_rect)
            
            # Draw score with animated highlight
            pulse = 1 + 0.1 * math.sin(time.time() * 3)
            score_font = pygame.font.Font(None, int(48 * pulse))
            score_text = score_font.render(f'Final Score: {self.snake.score}', True, WHITE)
            score_rect = score_text.get_rect(center=(WINDOW_SIZE/2, WINDOW_SIZE/2))
            self.screen.blit(score_text, score_rect)
            
            # Draw background for buttons
            button_bg = pygame.Surface((300, 180), pygame.SRCALPHA)
            button_bg.fill((0, 0, 0, 100))
            button_rect = button_bg.get_rect(center=(WINDOW_SIZE/2, WINDOW_SIZE/2 + 120))
            self.screen.blit(button_bg, button_rect)
            
            # Draw buttons with hover effects for options
            option_y = WINDOW_SIZE/2 + 60
            options = [
                ('Enter your name', 'ENTER'),
                ('Restart Game', 'R'),
                ('Return to Menu', 'ESC')
            ]
            
            for option, key in options:
                # Check if mouse is hovering over this option
                mouse_pos = pygame.mouse.get_pos()
                option_rect = pygame.Rect(WINDOW_SIZE/2 - 140, option_y, 280, 30)
                is_hovering = option_rect.collidepoint(mouse_pos)
                
                # Draw option with hover effect
                option_color = LIGHT_GREEN if is_hovering else WHITE
                option_text = self.font.render(option, True, option_color)
                option_rect = option_text.get_rect(center=(WINDOW_SIZE/2, option_y))
                self.screen.blit(option_text, option_rect)
                
                # Draw key hint
                key_bg = pygame.Rect(WINDOW_SIZE/2 + 120, option_y - 12, 40, 24)
                pygame.draw.rect(self.screen, DARK_GREEN if is_hovering else GRAY, key_bg, border_radius=5)
                key_text = self.small_font.render(key, True, WHITE)
                key_rect = key_text.get_rect(center=(WINDOW_SIZE/2 + 140, option_y))
                self.screen.blit(key_text, key_rect)
                
                option_y += 40
        else:
            # Draw name input with enhanced visuals
            # Background for input field
            input_bg = pygame.Surface((400, 200), pygame.SRCALPHA)
            input_bg.fill((0, 50, 0, 150))
            pygame.draw.rect(input_bg, GREEN, input_bg.get_rect(), 2, border_radius=10)
            input_bg_rect = input_bg.get_rect(center=(WINDOW_SIZE/2, WINDOW_SIZE/2))
            self.screen.blit(input_bg, input_bg_rect)
            
            # Title with animation
            name_pulse = 1 + 0.05 * math.sin(time.time() * 4)
            name_font = pygame.font.Font(None, int(36 * name_pulse))
            name_text = name_font.render('Enter your name:', True, WHITE)
            name_rect = name_text.get_rect(center=(WINDOW_SIZE/2, WINDOW_SIZE/2 - 60))
            self.screen.blit(name_text, name_rect)
            
            # Draw input field with border
            input_field = pygame.Rect(WINDOW_SIZE/2 - 150, WINDOW_SIZE/2 - 20, 300, 40)
            pygame.draw.rect(self.screen, BLACK, input_field)
            pygame.draw.rect(self.screen, GREEN, input_field, 2, border_radius=5)
            
            # Add text cursor with blinking effect
            input_text = self.font.render(self.player_name, True, WHITE)
            text_x = WINDOW_SIZE/2 - 140
            if self.player_name:
                text_x = max(text_x, WINDOW_SIZE/2 - input_text.get_width()/2)
            
            self.screen.blit(input_text, (text_x, WINDOW_SIZE/2 - 15))
            
            # Blinking cursor
            if int(time.time() * 2) % 2 == 0:
                cursor_x = text_x + input_text.get_width() + 2
                pygame.draw.line(self.screen, WHITE, 
                                (cursor_x, WINDOW_SIZE/2 - 15), 
                                (cursor_x, WINDOW_SIZE/2 + 15), 2)
            
            # Enter button with hover effect
            mouse_pos = pygame.mouse.get_pos()
            enter_button = pygame.Rect(WINDOW_SIZE/2 - 70, WINDOW_SIZE/2 + 40, 140, 40)
            is_hovering = enter_button.collidepoint(mouse_pos)
            
            pygame.draw.rect(self.screen, GREEN if is_hovering else DARK_GREEN, enter_button, border_radius=5)
            pygame.draw.rect(self.screen, WHITE, enter_button, 2, border_radius=5)
            
            enter_text = self.font.render('SAVE', True, WHITE)
            enter_rect = enter_text.get_rect(center=(WINDOW_SIZE/2, WINDOW_SIZE/2 + 60))
            self.screen.blit(enter_text, enter_rect)

    def draw_settings_screen(self):
        """Draw the settings screen with music theme options"""
        # Draw animated background
        self.screen.fill(BLACK)
        
        # Draw grid pattern for background
        for x in range(0, WINDOW_SIZE, GRID_SIZE*2):
            for y in range(0, WINDOW_SIZE, GRID_SIZE*2):
                offset = int(math.sin(time.time() * 1.5) * 3)
                rect = pygame.Rect(x + offset, y, GRID_SIZE, GRID_SIZE)
                pygame.draw.rect(self.screen, (0, 50, 0), rect)  # Very dark green
        
        # Create a semi-transparent overlay
        overlay = pygame.Surface((WINDOW_SIZE - 100, WINDOW_SIZE - 150), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        self.screen.blit(overlay, (50, 75))
        
        # Draw title
        title_text = self.large_font.render('SETTINGS', True, GREEN)
        title_rect = title_text.get_rect(center=(WINDOW_SIZE//2, 150))
        self.screen.blit(title_text, title_rect)
        
        # Draw subtitle
        subtitle_text = self.font.render('Music Theme', True, LIGHT_GREEN)
        subtitle_rect = subtitle_text.get_rect(center=(WINDOW_SIZE//2, 200))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        # Update button hover states
        self.music_orig_button.check_hover(pygame.mouse.get_pos())
        self.music_upbeat_button.check_hover(pygame.mouse.get_pos())
        self.music_adventure_button.check_hover(pygame.mouse.get_pos())
        self.settings_back_button.check_hover(pygame.mouse.get_pos())
        self.top_back_button.check_hover(pygame.mouse.get_pos())
        
        # Mark the currently selected music theme button
        self.music_orig_button.color = GREEN if self.selected_music_theme == MusicTheme.ORIGINAL else DARK_GREEN
        self.music_upbeat_button.color = GREEN if self.selected_music_theme == MusicTheme.UPBEAT else DARK_GREEN
        self.music_adventure_button.color = GREEN if self.selected_music_theme == MusicTheme.ADVENTURE else DARK_GREEN
        
        # Draw buttons
        self.music_orig_button.draw(self.screen, self.font)
        self.music_upbeat_button.draw(self.screen, self.font)
        self.music_adventure_button.draw(self.screen, self.font)
        self.settings_back_button.draw(self.screen, self.font)
        
        # Draw top back button
        self.top_back_button.draw(self.screen, self.small_font)
        
        # Add ESC key hint
        esc_hint = self.small_font.render("Press ESC to return to Menu", True, WHITE)
        self.screen.blit(esc_hint, (WINDOW_SIZE//2 - esc_hint.get_width()//2, 550))
        
        # Draw theme descriptions (improved layout)
        descriptions = [
            {"theme": MusicTheme.ORIGINAL, "title": "Original Theme:", "desc": "Classic snake game music - simple and nostalgic."},
            {"theme": MusicTheme.UPBEAT, "title": "Upbeat Theme:", "desc": "Energetic music with a faster tempo."},
            {"theme": MusicTheme.ADVENTURE, "title": "Adventure Theme:", "desc": "Epic soundtrack with sweeping melodies."}
        ]
        
        # Draw theme descriptions with visual indicators (clear spacing)
        y_pos = 460
        for desc in descriptions:
            is_selected = (desc["theme"] == self.selected_music_theme)
            # Position and draw the description box
            desc_box = pygame.Rect(WINDOW_SIZE//2 - 200, y_pos - 15, 400, 40)
            
            # Draw different background for selected theme
            if is_selected:
                pygame.draw.rect(self.screen, (0, 60, 0), desc_box)
                pygame.draw.rect(self.screen, GREEN, desc_box, 2, border_radius=5)
                # Draw a music note icon
                note_x = WINDOW_SIZE//2 - 180
                self.draw_music_note(note_x, y_pos + 5)
            else:
                pygame.draw.rect(self.screen, (0, 30, 0), desc_box)
            
            # Draw theme name and description
            theme_name = self.small_font.render(desc["title"], True, WHITE if is_selected else LIGHT_GREEN)
            theme_desc = self.small_font.render(desc["desc"], True, LIGHT_GREEN if is_selected else GRAY)
            
            self.screen.blit(theme_name, (WINDOW_SIZE//2 - 160, y_pos - 10))
            self.screen.blit(theme_desc, (WINDOW_SIZE//2 - 160, y_pos + 10))
            
            y_pos += 50

    def draw_music_note(self, x, y):
        """Draw a simple music note icon"""
        # Draw note head
        pygame.draw.ellipse(self.screen, LIGHT_GREEN, (x, y, 8, 6))
        # Draw note stem
        pygame.draw.line(self.screen, LIGHT_GREEN, (x+8, y+3), (x+8, y-12), 2)
        # Draw flag
        pygame.draw.arc(self.screen, LIGHT_GREEN, (x+6, y-12, 8, 8), 0, 3.14, 2)

    def run(self):
        """Main game loop with error handling"""
        try:
            # Ensure sounds are properly initialized
            if not self.sounds_loaded:
                print("Warning: Sound system failed to initialize properly. Game will run without sound.")
                
            # If background music failed to load but other sounds are ok, try loading music again
            if self.sounds_loaded and not self.background_music_loaded:
                print("Attempting to load background music again...")
                self._try_fallback_music()
                
            while True:
                if self.game_state == GameState.MENU:
                    self.handle_menu_events()
                    self.draw_menu()
                elif self.game_state == GameState.LEVEL_SELECT:
                    self.handle_level_select_events()
                    self.draw_level_select_screen()
                elif self.game_state == GameState.SETTINGS:
                    self.handle_settings_events()
                    self.draw_settings_screen()
                elif self.game_state == GameState.HIGHSCORE:
                    self.handle_highscore_events()
                    self.draw_highscore_screen()
                elif self.game_state == GameState.PLAYING:
                    self.handle_game_events()
                    
                    if not self.paused:
                        # Update score animations regardless of snake movement
                        self.snake.update_animations()
                        
                        result = self.snake.update()
                        if not result:
                            self.game_state = GameState.GAME_OVER
                            self.game_over = True  # Set game_over flag
                            if self.sounds_loaded:
                                # Don't stop the music at game over
                                # if self.background_music_loaded:
                                #     pygame.mixer.music.stop()
                                if self.game_over_sound:
                                    print("Playing game over sound...")
                                    self.game_over_sound.play()
                        elif self.snake.food != self.last_food_pos:
                            if self.sounds_loaded and self.eat_sound and self.snake.food is not None:
                                print("Playing eat sound...")
                                self.eat_sound.play()
                            self.last_food_pos = self.snake.food

                    self.screen.fill(BLACK)
                    self.snake.draw(self.screen)
                    self.draw_score()
                    
                    # Draw timer bar if not paused
                    if not self.paused:
                        self.snake.draw_timer(self.screen)
                    
                    if self.paused:
                        self.draw_pause_screen()
                
                elif self.game_state == GameState.GAME_OVER:
                    self.handle_game_over_events()
                    self.screen.fill(BLACK)
                    self.snake.draw(self.screen)
                    self.draw_score()
                    self.draw_game_over_screen()
                
                pygame.display.flip()
                self.clock.tick(FPS)
        except Exception as e:
            print(f"Error in main game loop: {e}")
            import traceback
            traceback.print_exc()
            
            # Try to clean up and exit gracefully
            try:
                pygame.quit()
            except:
                pass
            sys.exit(1)

if __name__ == '__main__':
    game = Game()
    game.run() 