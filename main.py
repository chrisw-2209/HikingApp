import sqlite3
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.spinner import Spinner

conn = sqlite3.connect('mountains.db')
cursor = conn.cursor()

class MountainScreen(Screen):
    def on_enter(self):
        self.show_mountains()
    def show_mountains(self):
        self.ids.mountain_list.clear_widgets()
        mountains = get_mountains()
        for mountain in mountains:
            label = Label(text=f"{mountain[1]} - {mountain[2]}")
            self.ids.mountain_list.add_widget(label)

class ClimbScreen(Screen):
    def on_enter(self):
        self.show_climbs()
    def show_climbs(self):
        self.ids.climb_list.clear_widgets()
        climbs = get_climbs()
        for climb in climbs:
            label = Label(text=f"{climb[1]} - {climb[2]}")
            self.ids.climb_list.add_widget(label)

class AddClimbScreen(Screen):
    selected_mountain_id = None
    def search_mountains(self, search_text):
        self.ids.mountain_results.clear_widgets()
        if search_text == "":
            return
        mountains = get_mountains()
        for mountain in mountains:
            if mountain[1].lower().startswith(search_text.lower()):
                button = Button(text=mountain[1])
                button.bind(
                    on_release=lambda x, mountain_id=mountain[0]:
                    self.select_mountain(mountain_id)
                )
                self.ids.mountain_results.add_widget(button)
                if len(self.ids.mountain_results.children) >= 10:
                    break
    def select_mountain(self, mountain_id):
        self.selected_mountain_id = mountain_id
        mountains = get_mountains()
        for mountain in mountains:
            if mountain[0] == mountain_id:
                self.ids.selected_mountain.text = f"Selected: {mountain[1]}"
                break
    def add_climb_from_form(self):
        date = self.ids.date_climbed.text
        time = self.ids.time_climbed.text
        add_climb(
            self.selected_mountain_id,
            date,
            time,
            None,
            None
        )
        popup = Popup(
            title="Climb Added",
            content=Label(text="Your climb has been added!"),
            size_hint=(0.6, 0.3)
        )
        popup.open()
        self.reset_form()
    def reset_form(self):
        self.selected_mountain_id = None
        self.ids.mountain_search.text = ""
        self.ids.date_climbed.text = ""
        self.ids.time_climbed.text = ""
        self.ids.selected_mountain.text = "No mountain selected"
        self.ids.mountain_results.clear_widgets()

class HikingApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(ClimbScreen(name="climbs"))
        sm.add_widget(AddClimbScreen(name="add_climb"))
        sm.add_widget(MountainScreen(name="mountains"))
        return sm

def create_tables():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS classifications (
        id INTEGER PRIMARY KEY,
        classification TEXT UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mountains (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE,
        height INTEGER,
        lat FLOAT,
        lon FLOAT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mountain_classifications (
        mountain_id INTEGER,
        classification_id INTEGER,
        FOREIGN KEY (mountain_id) REFERENCES mountains (id),
        FOREIGN KEY (classification_id) REFERENCES classifications (id),
        UNIQUE (mountain_id, classification_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS climbs (
        id INTEGER PRIMARY KEY,
        mountain_id INTEGER,
        date_climbed TEXT,
        time_climbed TEXT,
        lat_checked_in FLOAT,
        lon_checked_in FLOAT,
        FOREIGN KEY (mountain_id) REFERENCES mountains (id)
    )
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO classifications (classification)
    VALUES
        ('w3000'),
        ('marilyn');
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO mountains (name, height, lat, lon)
    VALUES
        ('snowdon', 1085, 53.0685,-4.0763),
        ('garnedd ugain', 1065, 53.0754,-4.0757),
        ('aran fawddwy', 905, 52.7847,-3.6881)

    """)

    mountain_data = [
        ("snowdon", ["w3000", "marilyn"]),
        ("garnedd ugain", ["w3000"]),
        ("aran fawddwy", ["marilyn"])
    ]

    for mountain_name, classifications in mountain_data:
        cursor.execute("""
            SELECT id
            FROM mountains
            WHERE name = ?
        """,(
            mountain_name,
        ))
        mountain_id = cursor.fetchone()[0]
        for classification_name in classifications:
            cursor.execute("""
                SELECT id
                FROM classifications
                WHERE classification = ?    
            """,(
                classification_name,
            ))
            classification_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT OR IGNORE INTO mountain_classifications
                    (mountain_id, classification_id)
                VALUES
                    (?, ?)
            """, (
                mountain_id, classification_id,
            ))
    conn.commit()

def coordinate_check(latitude, longitude):
    tolerance = 0.001
    cursor.execute("""
        SELECT * FROM mountains WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
    """,(
        latitude-tolerance, latitude+tolerance, longitude-tolerance, longitude+tolerance,
    ))
    mountains = cursor.fetchall()
    if not mountains:
        return None
    shortest_distance = (( mountains[0][3] - latitude )**2 + (mountains[0][4] - longitude)**2 ) ** 0.5
    closest = mountains[0]
    for mountain in mountains:
        distance = (( mountain[3] - latitude )**2 + (mountain[4] - longitude)**2 ) ** 0.5
        if distance < shortest_distance: 
            shortest_distance = distance
            closest = mountain
    return closest[0], shortest_distance

def add_climb(mountain_id, date_climbed, time_climbed, latitude, longitude):
    cursor.execute("""
        INSERT INTO climbs (mountain_id, date_climbed, time_climbed, lat_checked_in, lon_checked_in)
        VALUES
            (?,?,?,?,?)    
    """, (
        mountain_id,
        date_climbed,
        time_climbed,
        latitude,
        longitude
    ))
    conn.commit()

def get_climbs():
    cursor.execute("""
        SELECT climbs.id, mountains.name, climbs.date_climbed
        FROM climbs
        JOIN mountains ON climbs.mountain_id = mountains.id
    """)
    return cursor.fetchall()

def get_mountains():
    cursor.execute("""
        SELECT * FROM mountains
    """)
    return cursor.fetchall()

def main():
    create_tables()
    #add_climb(1, "2026-08-22", "14:30", 53.0685, -4.0763)
    HikingApp().run()    

if __name__== "__main__":
    main() 







