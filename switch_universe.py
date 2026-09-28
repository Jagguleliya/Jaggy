"""
Switch or customize the story universe for the YouTube Shorts movie series.
"""
import sys
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
universe_file = os.path.join(BASE_DIR, 'data', 'story_universe.json')

UNIVERSES = {
    "1": {
        "name": "THE ECHO PROTOCOL",
        "genre": "Sci-Fi Mystery / Time Anomaly Thriller",
        "logline": "A signals analyst monitoring deep-space frequencies decodes emergency broadcasts sent from his own future timeline, warning of an extinction event happening in 24 hours.",
        "setting": "Sub-level 4 Listening Post, Blackwood Observatory, isolated in dense pine forest. Cold War analog technology mixed with anomalous deep-space sensors.",
        "protagonist": "Dr. Elias Vance (Observer-7)",
        "antagonist_or_threat": "The Echo—a conscious radio frequency from an alternate timeline that alters physical reality.",
        "current_episode": 0,
        "episodes": []
    },
    "2": {
        "name": "PROJECT DEEP TRENCH",
        "genre": "Cosmic Horror / Deep Ocean Expedition",
        "logline": "A deep-sea submarine research crew descends to 11,000 meters in the Mariana Trench and discovers an ancient, colossal vault door that is slowly opening from the inside.",
        "setting": "Titan-Class Exploration Submersible 'Nautilus-IV' in total abyssal darkness, navigating jagged tectonic rifts with flickering searchlights.",
        "protagonist": "Captain Noah Reed & Sonar Specialist Elena Vance",
        "antagonist_or_threat": "The Abyssal Entity—a pre-human intelligence slumbering beneath the seabed.",
        "current_episode": 0,
        "episodes": []
    },
    "3": {
        "name": "THE BLACK BOX ARCHIVES",
        "genre": "Classified Government Mystery / Found Footage ARG",
        "logline": "Declassified audio recovery logs and incident reports of anomalous phenomena and impossible items that the government erased from history between 1962 and 1999.",
        "setting": "Redacted Department of Anomalous Containment (DAC) underground archives.",
        "protagonist": "The Archivist (Whistleblower)",
        "antagonist_or_threat": "Classified Item-088—an object that erases memories of anyone who touches it.",
        "current_episode": 0,
        "episodes": []
    }
}

def main():
    print("========================================================")
    print("  Choose Your YouTube Shorts Movie Saga Universe")
    print("========================================================")
    print("1. THE ECHO PROTOCOL (Sci-Fi Time Anomaly / Signal from Tomorrow)")
    print("2. PROJECT DEEP TRENCH (Cosmic Deep-Sea Mystery / Vault at 11,000m)")
    print("3. THE BLACK BOX ARCHIVES (Classified Government Coverup / Found Footage)")
    print("========================================================")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    if choice not in UNIVERSES:
        print("Invalid choice. Keeping current universe.")
        return
        
    selected = UNIVERSES[choice]
    os.makedirs(os.path.dirname(universe_file), exist_ok=True)
    with open(universe_file, 'w', encoding='utf-8') as f:
        json.dump(selected, f, indent=2)
        
    print(f"\nSuccessfully activated Universe: {selected['name']}!")
    print(f"Genre: {selected['genre']}")
    print(f"Ready for Episode 1 (Part 1). Run 'run_story.bat' to generate!")

if __name__ == '__main__':
    main()
