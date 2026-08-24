import sqlite3
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.metrics import sp, dp
from kivy.uix.checkbox import CheckBox
from kivy.uix.widget import Widget
from kivy.clock import Clock

conn = sqlite3.connect('mountains.db')
cursor = conn.cursor()

class ClimbLabel(Label):
    def __init__(
        self,
        climb_id,
        mountain_name,
        date_climbed,
        on_delete,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.climb_id = climb_id
        self.mountain_name = mountain_name
        self.date_climbed = date_climbed
        self.on_delete = on_delete

        self.long_press_event = None
        self.touch_start_pos = None
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.touch_start_pos = touch.pos
            self.long_press_event = Clock.schedule_once(
                lambda dt: self.long_press(),
                0.8
            )
        return super().on_touch_down(touch)
    def on_touch_move(self, touch):
        if hasattr(self, "touch_start_pos"):
            start_x, start_y = self.touch_start_pos
            current_x, current_y = touch.pos
            distance = ((current_x - start_x) ** 2 +
                        (current_y - start_y) ** 2) ** 0.5
            if distance > dp(15):
                if self.long_press_event:
                    self.long_press_event.cancel()
                    self.long_press_event = None
        return super().on_touch_move(touch)
    def delete_pressed(self, popup):
        delete_climb(self.climb_id)
        popup.dismiss()
        self.on_delete()
    def long_press(self):
        content = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(10)
        )
        message = Label(
            text=f"Delete climb {self.mountain_name} on {self.date_climbed}"
        )
        buttons = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50)
        )
        cancel_button = Button(text="Cancel")
        delete_button = Button(text="Delete")
        buttons.add_widget(cancel_button)
        buttons.add_widget(delete_button)
        content.add_widget(message)
        content.add_widget(buttons)
        popup = Popup(
            title="Delete Climb?",
            content=content,
            size_hint=(0.6, 0.3)
        )
        cancel_button.bind(on_release=popup.dismiss)
        delete_button.bind(
            on_release=lambda instance: self.delete_pressed(popup)
        )
        popup.open()

class TabBar(TabbedPanel):
    pass

class Home(BoxLayout):
    pass

class Statistics(BoxLayout):
    pass

class Mountains(BoxLayout):
    sort_by = "height"
    descending = True
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.classification_checkboxes = {}

    def on_kv_post(self, base_widget):

        self.create_classification_filters()
        self.show_mountains()

    def create_classification_filters(self):
        classifications = get_classifications()
        for classification in classifications:
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                size_hint_x=None,
                width=dp(140),
                height=dp(40)
            )
            lbl = Label(
                text=classification,
                font_size=sp(16),
                size_hint_x = None,
                width = dp(100)
            )
            chk = CheckBox(
                active=True,
                size_hint_x=None,
                width=dp(40)
            )
            chk.bind(active=self.checkbox_changed)
            self.classification_checkboxes[classification] = chk
            row.add_widget(lbl)
            row.add_widget(chk)
            self.ids.classification_filters.add_widget(row)
    def checkbox_changed(self, checkbox, value):
        #selected = self.get_selected_classifications()
        #print(selected)
        self.show_mountains()
    def get_selected_classifications(self):
        selected = []
        for classification, checkbox in self.classification_checkboxes.items():
            if checkbox.active:
                selected.append(classification)
        return selected
    def sort_mountains(self, sort_by, descending):
        self.sort_by = sort_by
        self.descending = descending
        self.show_mountains()
    def show_mountains(self):
        self.ids.mountain_list.clear_widgets()
        selected = self.get_selected_classifications()
        mountains = get_mountains(
            selected,
            self.sort_by,
            self.descending
        )
        for mountain in mountains:
            label = Label(
                text=f"{mountain[1]} - {mountain[2]}m",
                size_hint_y=None,
                height=dp(45),
                font_size=sp(16)
            )
            self.ids.mountain_list.add_widget(label)

class Climbs(BoxLayout):
    sort_by = "date"
    descending = True
    classification_checkboxes = {}
    def on_kv_post(self, base_widget):
        self.create_classification_filters()
        self.show_climbs()
    def create_classification_filters(self):
        classifications = get_classifications()
        for classification in classifications:
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                size_hint_x=None,
                height=dp(40),
                width=dp(140)
            )
            lbl = Label(
                text=classification,
                font_size=sp(16),
                size_hint_x = None,
                width = dp(100)
            )
            chk = CheckBox(
                active=True,
                size_hint_x=None,
                width=dp(40)
            )
            chk.bind(active=self.checkbox_changed)
            self.classification_checkboxes[classification] = chk
            row.add_widget(lbl)
            row.add_widget(chk)
            self.ids.classification_filters.add_widget(row)
    def get_selected_classifications(self):
        selected = []
        for classification, checkbox in self.classification_checkboxes.items():
            if checkbox.active:
                selected.append(classification)
        return selected
    def checkbox_changed(self, checkbox, active):
        self.show_climbs()
    def sort_climbs(self, sort_by, descending):
        print("SORT:", sort_by, descending)
        self.sort_by = sort_by
        self.descending = descending
        self.show_climbs()
    def show_climbs(self):
        self.ids.climb_list.clear_widgets()
        selected = self.get_selected_classifications()
        search = self.ids.climb_search.text
        climbs = get_climbs(
            selected,
            search,
            self.sort_by,
            self.descending
        )
        for climb in climbs:
            label = ClimbLabel(
                climb_id=climb[0],
                mountain_name=climb[1],
                date_climbed=climb[2],
                on_delete=self.show_climbs,
                text=f"{climb[1]} - {climb[2]}",
                size_hint_y=None,
                height=dp(45),
                font_size=sp(16)
            )
            self.ids.climb_list.add_widget(label)

class AddClimbs(BoxLayout):
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
        return TabBar()

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
        ('aran fawddwy', 905, 52.7847,-3.6881),
        ('carnedd llewelyn', 1064, 53.1583,-3.9681),
        ('carnedd dafydd', 1044, 53.1474,-4.0008),
        ('glyder fawr', 1011, 53.1258,-4.0322)
    """)

    mountain_data = [
        ("snowdon", ["w3000", "marilyn"]),
        ("garnedd ugain", ["w3000"]),
        ("aran fawddwy", ["marilyn"]),
        ("carnedd llewelyn", ["w3000", "marilyn"]),
        ("carnedd dafydd", ["w3000"]),
        ("glyder fawr", ["w3000", "marilyn"]),
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

def get_climbs(selected=None, search=None, sort_by="date", descending=True):
    query = """
        SELECT DISTINCT
            climbs.id,
            mountains.name,
            climbs.date_climbed,
            climbs.time_climbed,
            climbs.lat_checked_in,
            climbs.lon_checked_in
        FROM climbs
        JOIN mountains
            ON climbs.mountain_id = mountains.id
    """
    parameters = []
    if selected:
        placeholders = ",".join("?" for _ in selected)
        query += f"""
            JOIN mountain_classifications
                ON mountains.id = mountain_classifications.mountain_id
            JOIN classifications
                ON mountain_classifications.classification_id = classifications.id
            WHERE classifications.classification IN ({placeholders})
        """
        parameters.extend(selected)
    if search:
        if selected:
            query += " AND mountains.name LIKE ?"
        else:
            query += " WHERE mountains.name LIKE ?"
        parameters.append(f"%{search}%")
    direction = "DESC" if descending else "ASC"
    query += f" ORDER BY climbs.date_climbed {direction}"
    cursor.execute(query, parameters)
    return cursor.fetchall()

def get_mountains(classifications=None, sort_by="name", descending=False):
    query ="""
        SELECT DISTINCT mountains.*
        FROM mountains
    """
    parameters = []
    if classifications:
        placeholders = ",".join("?" for _ in classifications)
        query += f"""
            JOIN mountain_classifications
                ON mountains.id = mountain_classifications.mountain_id
            JOIN classifications
                ON mountain_classifications.classification_id = classifications.id
            WHERE classifications.classification IN ({placeholders})
        """
        parameters.extend(classifications)
    sort_options = {
        "name":"mountains.name",
        "height":"mountains.height"
    }
    sort_column = sort_options.get(sort_by, "mountains.name")
    direction = "DESC" if descending else "ASC"
    query += f"ORDER BY {sort_column} {direction}"
    cursor.execute(query, parameters)
    return cursor.fetchall()

def get_classifications():
    cursor.execute("""
        SELECT classification
        FROM classifications
        ORDER BY classification
    """)
    return [row[0] for row in cursor.fetchall()]

def delete_climb(climb_id):
    query = """
        DELETE FROM climbs
        WHERE id = ?
    """
    cursor.execute(query, (climb_id,))
    conn.commit()

def main():
    create_tables()
    #add_climb(1, "2026-08-22", "14:30", 53.0685, -4.0763)
    HikingApp().run()    

if __name__== "__main__":
    main() 
