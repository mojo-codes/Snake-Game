import json
import os

class HighscoreManager:
    def __init__(self):
        self.highscores = []
        self.filename = "highscores.json"
        self.load_highscores()

    def load_highscores(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.highscores = json.load(f)
            except:
                self.highscores = []
        else:
            self.highscores = []

    def save_highscores(self):
        with open(self.filename, 'w') as f:
            json.dump(self.highscores, f)

    def add_score(self, name, score):
        self.highscores.append({"name": name, "score": score})
        self.highscores.sort(key=lambda x: x["score"], reverse=True)
        self.highscores = self.highscores[:10]  # Keep only top 10
        self.save_highscores()

    def get_highscores(self):
        return self.highscores 