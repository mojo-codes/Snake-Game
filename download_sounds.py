import os
import requests

def download_sound(url, filename):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Downloaded {filename}")
        else:
            print(f"❌ Failed to download {filename}: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error downloading {filename}: {e}")

def main():
    if not os.path.exists('sounds'):
        os.makedirs('sounds')

    sounds = {
        'eat.wav': 'https://raw.githubusercontent.com/robdouglas/audio-files/main/coin.wav',
        'game_over.wav': 'https://raw.githubusercontent.com/robdouglas/audio-files/main/fail.wav',
        'pause.wav': 'https://raw.githubusercontent.com/robdouglas/audio-files/main/pause.wav',
        'background.wav': 'https://raw.githubusercontent.com/robdouglas/audio-files/main/background-music.wav'
    }

    print("🎧 Starting sound download...")
    for filename, url in sounds.items():
        download_sound(url, os.path.join('sounds', filename))

    print("✅ Download complete!")

if __name__ == '__main__':
    main()
