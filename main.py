import sqlite3
import csv
import os
import math
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
from kivy_garden.mapview import MapView, MapMarkerPopup, MapSource, MapMarker
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from datetime import datetime
from kivy.clock import Clock, mainthread
from kivy.uix.textinput import TextInput
from kivy.utils import platform
from kivy.core.window import Window
from plyer import gps
from datetime import datetime
from kivy.uix.recycleview import RecycleView

if platform != "android":
    Window.size = (500, 1000)

__version__ = "1.1.1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(BASE_DIR, "mountain_data.csv")
Window.softinput_mode = "below_target"
classification_display_names = {
    "w3000": "Welsh 3000",
    "hewitt": "Hewitt",
    "marilyn": "Marilyn",
    "nuttall": "Nuttall", 
}

class MountainButton(Button):
    mountain_id = NumericProperty()
    on_select = ObjectProperty(None)
    def on_release(self):
        if self.on_select:
            self.on_select(self.mountain_id)

class LocationManager:
    def __init__(self):
        self.latitude = None
        self.longitude = None
        self.accuracy = None
    def start(self):
        print("TEST GPS STARTING")
        if platform == "android":
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION
            ], self.permission_callback)
        else:
            print("TEST GPS only available on Android")
    def permission_callback(self, permissions, results):
        if all(results):
            self.configure_gps()
        else:
            print("TEST GPS Permissions denied!")
    def configure_gps(self):
        print("TEST GPS Configuring")
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        activity = PythonActivity.mActivity
        location_manager = activity.getSystemService(
            Context.LOCATION_SERVICE
        )
        providers = location_manager.getProviders(False)
        for provider in providers:
            print(
                "GPS PROVIDER:",
                provider,
                "enabled:",
                location_manager.isProviderEnabled(provider)
            )
        try:
            gps.configure(
                on_location=self.on_location,
                on_status=self.on_status
            )
            print("TEST GPS CONFIGURED")
            gps.start(1000, 0)
            print("TEST GPS STARTED")
        except NotImplementedError:
            print("GPS is not implemented on this platform")
    def on_location(self, **kwargs):
        self.latitude = kwargs.get("lat")
        self.longitude = kwargs.get("lon")
        self.accuracy = kwargs.get("accuracy")
        print("GPS CALLBACK:", kwargs)
        print(
            f"GPS LOCATION: {self.latitude}, "
            f"{self.longitude}, accuracy: {self.accuracy}"
        )
    @mainthread
    def on_status(self, stype, status):
        print("GPS STATUS:", stype, status)
    def on_pause(self):
        if platform == "android":
            gps.stop()
        return True
    def on_resume(self):
        if platform == "android":
            gps.start(min_time=1000, min_distance=1)

class DateInput(TextInput):
    def do_backspace(self, from_undo=False, mode='bkspc'):
        if self.text.endswith("-"):
            self.text = self.text[:-2]
            self.cursor = self.get_cursor_from_index(len(self.text))
            return
        return super().do_backspace(from_undo=from_undo, mode=mode)

class TimeInput(TextInput):
    def do_backspace(self, from_undo=False, mode='bkspc'):
        if self.text.endswith(":"):
            self.text = self.text[:-2]
            self.cursor = self.get_cursor_from_index(len(self.text))
            return
        return super().do_backspace(from_undo=from_undo, mode=mode)                

class ClimbButton(Button):
    __events__ = ('on_long_press',)
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
            self._clockev = None
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
                on_release=lambda instance: (delete_climb(self.climb_id),popup.dismiss(),self.on_delete())
            )
            popup.open()
    def on_state(self, instance, value):
        if value == "down":
            lpt = 0.8
            self._clockev = Clock.schedule_once(self._do_long_press,lpt)
        else:
            if self._clockev:
                self._clockev.cancel()
    def _do_long_press(self,dt):
        self.dispatch('on_long_press')
    def on_long_press(self,*largs):
        self.long_press()
        pass
    
class MountainMarker(MapMarkerPopup):
    mountain_name = StringProperty("")
    elevation = NumericProperty(0)
    mountain_id = NumericProperty(0)
    def __init__(self, mountain_id, mountain_name, elevation, **kwargs):
        super().__init__(**kwargs)
        self.mountain_id = mountain_id
        self.mountain_name = mountain_name
        self.elevation = elevation
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.is_double_tap:
            print("double tap on this marker")
            return super().on_touch_down(touch)
        return False

class TabBar(TabbedPanel):
    pass

class Home(BoxLayout):
    climbed_checkboxes = {}
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.open_marker = None
        self.mapview = None
        self.markers = []
        self.climbed_filter = None
        self.active_map_touches = {}
        self.map_touch_start = None
        self.was_dragged = False
        self.location_marker = None
    def on_kv_post(self, base_widget):
        self.create_climbed_filters()
        self.show_map()
        self.show_markers()
        Clock.schedule_interval(self.show_marker_location, 1)
    def show_marker_location(self,_dt):
        app = App.get_running_app()
        lat = app.location_manager.latitude
        lon = app.location_manager.longitude
        if lat is None or lon is None:
            return
        if self.location_marker == None:
            self.location_marker = MapMarker(
                lat=lat,
                lon=lon,
                source = "kivy_garden/mapview/icons/location.png"
            )
            self.mapview.add_marker(self.location_marker)
        else:
            self.location_marker.lat = lat
            self.location_marker.lon = lon
    def set_climbed_filter(self, climbed):
        self.climbed_filter = climbed
        self.show_markers()
    def show_map(self):
        self.ids.map_container.clear_widgets()
        osm_source = MapSource(
            url="https://tile.opentopomap.org/{z}/{x}/{y}.png",
            cache_key="osm",
            min_zoom=1,
            max_zoom=17,
            tile_size=256,
            image_ext="png"
        )
        self.mapview = MapView(
            zoom=8,
            lat=52.33022,
            lon=-3.76641,
            map_source=osm_source
        )
        self.ids.map_container.add_widget(self.mapview)
    def get_selected_classifications(self):
        selected = []
        for classification, checkbox in self.climbed_checkboxes.items():
            if checkbox.active:
                selected.append(classification)
        return selected
    def show_markers(self):
        for marker in self.markers:
            self.mapview.remove_marker(marker)
        self.markers = []
        selected = self.get_selected_classifications()
        if not selected:
            return
        for mountain in get_mountains(selected,self.climbed_filter):
            temp_marker = MountainMarker(
                mountain_id=mountain[0],
                mountain_name=mountain[1],
                elevation=mountain[2],
                lat=mountain[3],
                lon=mountain[4]
                )
            temp_marker.mapview = self.mapview
            temp_marker.bind(
                on_release=lambda marker: self.marker_pressed(marker)
            )       
            self.mapview.add_marker(temp_marker)
            self.markers.append(temp_marker)
    def marker_pressed(self, marker):
        if self.open_marker is not None and self.open_marker != marker:
            self.open_marker.is_open = False
        self.open_marker = marker
    def checkbox_changed(self, checkbox, active):
        self.show_markers()
    def create_climbed_filters(self):
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
                    text=class_name(classification),
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
                self.climbed_checkboxes[classification] = chk
                row.add_widget(lbl)
                row.add_widget(chk)
                self.ids.map_filters.add_widget(row)
    def refresh_home(self):
        self.show_map()
        self.show_markers()
    def map_touch_down(self, touch):
        if self.mapview.collide_point(*touch.pos):
            self.map_touch_start = touch.pos
            self.was_dragged = False
    def map_touch_move(self, touch):
        if self.map_touch_start is None:
            return
        start_x, start_y = self.map_touch_start
        current_x, current_y = touch.pos
        distance = ((start_x - current_x)**2 + (start_y - current_y)**2) ** 0.5
        if distance > dp(15):
            self.was_dragged = True
    def map_touch_up(self, touch):
        if self.map_touch_start is None:
            return
        if not self.was_dragged:
            if self.open_marker is not None:
                self.open_marker.is_open = False
                self.open_marker = None
        self.map_touch_start = None
        self.was_dragged = False
    def update_location_marker(self):
        app = App.get_running_app()
        self.curr_lat = app.location_manager.latitude
        self.curr_lon = app.location_manager.longitude
        self.curr_acc = app.location_manager.accuracy
    def map_zoom_in(self):
        if self.mapview.zoom <17:
            self.mapview.zoom += 1
    def map_zoom_out(self):
        if self.mapview.zoom >1:
            self.mapview.zoom -= 1
    def map_centre(self):
        app = App.get_running_app()
        lat = app.location_manager.latitude
        lon = app.location_manager.longitude
        if lat is not None and lon is not None:
            self.mapview.center_on(lat, lon)

class Statistics(BoxLayout):
    def on_kv_post(self, base_widget):
        self.show_statistics()
    def show_statistics(self):
        self.ids.statistic_table.clear_widgets()
        statistics = get_statistics() 
        for classification in statistics:
            climb_percent = round((classification[2] / classification[1]) *100,1)
            label = Label(
                text=f"{class_name(classification[0])} - {classification[2]}/{classification[1]} - {climb_percent}%",
                size_hint_y = None,
                height = dp(45)
            )
            self.ids.statistic_table.add_widget(label)

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
                text=class_name(classification),
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
        if not selected:
            return
        mountains = get_mountains(
            classifications=selected,
            climbed=None,
            sort_by=self.sort_by,
            descending=self.descending
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
                text=class_name(classification),
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
            label = ClimbButton(
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
    def reset_search(self):
        self.ids.climb_search.text = ""
        self.show_climbs()

class AddClimbs(BoxLayout):
    selected_mountain_id = None
    def search_mountains(self, search_text):
        mountains = get_mountains()
        data = []
        for mountain in mountains:
            if mountain[1].lower().startswith(search_text.lower()):
                data.append({
                    "text":mountain[1],
                    "mountain_id":mountain[0],
                    "on_select":self.select_mountain
                })        
        self.ids.mountain_results.data=data
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
        if not self.selected_mountain_id:
            popup_nomountain = Popup(
                title="Warning",
                content=Label(text="No Mountain Selected"),
                size_hint=(0.6,0.3)
            )
            popup_nomountain.open()
            return
        if not date:
            popup_date = Popup(
                title="Warning",
                content=Label(text="No Date Selected"),
                size_hint=(0.6,0.3)
            )
            popup_date.open()
            return
        try:
            datetime.strptime(date,"%Y-%m-%d")
        except ValueError:
            popup_dateformat = Popup(
                title="Warning",
                content=Label(text="Please use YYYY-MM-DD"),
                size_hint=(0.6,0.3)
            )
            popup_dateformat.open()
            return
        if time:
            try:
                datetime.strptime(time,"%H:%M")

            except ValueError:
                popup_timeformat = Popup(
                    title="Warning",
                    content=Label(text="Please use HH:MM"),
                    size_hint=(0.6,0.3)
                )
                popup_timeformat.open()
                return
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
    def reset_search(self):
        self.ids.mountain_search.text = ""
    def format_date(self, text):
        formatted_text = ''.join([char for char in text if char.isdigit()])
        if len(formatted_text) < 4:
            return formatted_text
        elif len(formatted_text) == 4:
            return formatted_text+"-"
        elif len(formatted_text) < 6:
            return formatted_text[0:4]+"-"+formatted_text[4:]
        elif len(formatted_text) == 6:
            return formatted_text[0:4]+"-"+formatted_text[4:]+"-"
        else:
            return formatted_text[0:4]+"-"+formatted_text[4:6]+"-"+formatted_text[6:8]
    def update_date_text(self, text_input):
        formatted = self.format_date(text_input.text)
        if text_input.text != formatted:
            text_input.text = formatted
            Clock.schedule_once(
                lambda dt: setattr(
                    text_input,
                    "cursor",
                    text_input.get_cursor_from_index(len(formatted))
                ),
                0
            )
    def format_time(self,text):
        formatted_text = ''.join([char for char in text if char.isdigit()])
        if len(formatted_text) < 2:
            return formatted_text
        elif len(formatted_text) == 2:
            return formatted_text+":"
        else:
            return formatted_text[:2]+":"+formatted_text[2:]
    def update_time_text(self, text_input):
        formatted = self.format_time(text_input.text)
        if text_input.text != formatted:
            text_input.text = formatted
            Clock.schedule_once(
                lambda dt: setattr(
                    text_input,
                    "cursor",
                    text_input.get_cursor_from_index(len(formatted))
                ),
                0
            )
    def add_climb_auto(self):
        app = App.get_running_app()
        now = datetime.now()
        self.curr_lat = app.location_manager.latitude
        self.curr_lon = app.location_manager.longitude
        self.curr_acc = app.location_manager.accuracy
        self.curr_date = now.strftime("%Y-%m-%d")
        self.curr_time = now.strftime("%H:%M")
        content = BoxLayout(
            orientation = "vertical",
            spacing = dp(10),
            padding = dp(10)
        )
        buttons = BoxLayout(
            orientation = "horizontal",
            size_hint_y = None,
            height = dp(50)
        )
        if self.curr_lat is None or self.curr_lon is None:
            message = Label(
                text=f"No Location Available\nPlease turn on location services"
            )
            ok_button = Button(text="OK")
            buttons.add_widget(ok_button)
            content.add_widget(message)
            content.add_widget(buttons)
            popup = Popup(
                title="ERROR!",
                content=content,
                size_hint=(0.6, 0.3)
            )
            ok_button.bind(on_release=popup.dismiss)
            popup.open()
            return
        if self.curr_acc is None or self.curr_acc > 20:
            message = Label(
                text=f"Location not accurate enough\nPlease try again\nAccuracy: {self.curr_acc}"
            )
            ok_button = Button(text="OK")
            buttons.add_widget(ok_button)
            content.add_widget(message)
            content.add_widget(buttons)
            popup = Popup(
                title="ERROR!",
                content=content,
                size_hint=(0.6, 0.3)
            )
            ok_button.bind(on_release=popup.dismiss)
            popup.open()
            return
        mountain = coordinate_check(self.curr_lat, self.curr_lon)
        if mountain is None:
            message = Label(
                text=f"No Mountain Found!"
            )
            ok_button = Button(text="OK")
            buttons.add_widget(ok_button)
            content.add_widget(message)
            content.add_widget(buttons)
            popup = Popup(
            title="ERROR!",
            content=content,
            size_hint=(0.6, 0.3)
            )
            ok_button.bind(on_release=popup.dismiss)
            popup.open()
            return
        mountain_id, mountain_name, distance, mlat, mlon = mountain
        if distance < 10:
            message = Label(
                text=f"Add Mountain: {mountain_name}?"
            )
            cancel_button = Button(text="Cancel")
            add_button = Button(text="Add Climb")
            buttons.add_widget(cancel_button)
            buttons.add_widget(add_button)
            content.add_widget(message)
            content.add_widget(buttons)
            popup = Popup(
                title="Confirm Climb",
                content=content,
                size_hint=(0.6, 0.3)
            )
            cancel_button.bind(on_release=popup.dismiss)
            add_button.bind(
                on_release=lambda instance: (
                    add_climb(
                        mountain_id,
                        self.curr_date,
                        self.curr_time,
                        self.curr_lat,
                        self.curr_lon
                    ),
                    popup.dismiss()
                )
            )
            popup.open()
        else:
            message = Label(
                text=f"Too far away\nDistance: {round(distance,0)}m\n{bearing(self.curr_lat,self.curr_lon,mlat,mlon)}"
            )
            ok_button = Button(text="OK")
            buttons.add_widget(ok_button)
            content.add_widget(message)
            content.add_widget(buttons)
            popup = Popup(
                title="ERROR!",
                content=content,
                size_hint=(0.6, 0.3)
            )
            ok_button.bind(on_release=popup.dismiss)
            popup.open()
        return

class HikingApp(App):
    def build(self):
        self.location_manager = LocationManager()
        return TabBar()
    def on_start(self):
        self.location_manager.start()

def create_tables():
#==========OPEN CSV FILE===========================================================================================
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        mountains = list(csv.DictReader(csvfile))

#==========CREATE SQL TABLES========================================================================================
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

#==========CLEAR REFERENCE RELATIONSHIPS============================================================
    cursor.execute("""
        DELETE FROM mountain_classifications
    """)

    cursor.execute("""
        DELETE FROM classifications
    """)

#==========ADD CLASSIFICATIONS TO CLASSIFICATION TABLE============================================
    classifications_data = []
    query = """
    INSERT OR IGNORE INTO classifications (classification)
    VALUES (?)
    """
    for mountain in mountains:
        for classification in mountain["Classification"].split(","):
            classification = classification.strip()
            if (classification,) not in classifications_data:
                classifications_data.append((classification,))
    cursor.executemany(query,classifications_data)

#==========ADD NAME, HEIGHT, LAT AND LON TO MOUNTAIN TABLE======================================
    mountains_table_data = []
    query =   """INSERT INTO mountains (name, height, lat, lon)
        VALUES (?,?,?,?)
        ON CONFLICT(name)
        DO UPDATE SET
            height = excluded.height,
            lat = excluded.lat,
            lon = excluded.lon
    """
    for mountain in mountains:
        mountains_table_data.append(
            (
                mountain["Name"],
                int(mountain["Height"]),
                float(mountain["Latitude"]),
                float(mountain["Longitude"])
            )
        )
    cursor.executemany(query, mountains_table_data)

#==========REBUILD MOUNTAIN CLASSIFICATIONS========================================================
    mountain_data = []

    for mountain in mountains:

        classifications = [
            classification.strip()
            for classification in mountain["Classification"].split(",")
        ]

        mountain_data.append(
            (
                mountain["Name"],
                classifications
            )
        )


    for mountain_name, classifications in mountain_data:

        # Find the database ID for this mountain
        cursor.execute("""
            SELECT id
            FROM mountains
            WHERE name = ?
        """, (
            mountain_name,
        ))

        mountain_id = cursor.fetchone()[0]


        for classification_name in classifications:

            # Find the database ID for this classification
            cursor.execute("""
                SELECT id
                FROM classifications
                WHERE classification = ?
            """, (
                classification_name,
            ))

            classification_id = cursor.fetchone()[0]


            # Create the relationship between the two IDs
            cursor.execute("""
                INSERT OR IGNORE INTO mountain_classifications
                    (mountain_id, classification_id)
                VALUES (?, ?)
            """, (
                mountain_id,
                classification_id
            ))


#==========UPDATE THE DATABASE=======================================================================
    conn.commit()

def get_database_connection():
    app = App.get_running_app()
    db_path = os.path.join(app.user_data_dir, "mountains.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    return conn, cursor

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
    shortest_distance = haversine(latitude,longitude,mountains[0][3],mountains[0][4])
    closest = mountains[0]
    for mountain in mountains:
        distance = haversine(latitude,longitude,mountain[3],mountain[4])
        if distance < shortest_distance: 
            shortest_distance = distance
            closest = mountain
    return closest[0],closest[1], shortest_distance, closest[3], closest[4]

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

def get_mountains(classifications=None, climbed=None, sort_by="name", descending=False):
    query = """
        SELECT DISTINCT mountains.*
        FROM mountains
    """
    parameters = []
    conditions = []
    if classifications:
        placeholders = ",".join("?" for _ in classifications)
        query += """
            JOIN mountain_classifications
                ON mountains.id = mountain_classifications.mountain_id
            JOIN classifications
                ON mountain_classifications.classification_id = classifications.id
        """
        conditions.append(f"classifications.classification IN ({placeholders})")
        parameters.extend(classifications)
    query += """
        LEFT JOIN climbs
            ON mountains.id = climbs.mountain_id
    """
    if climbed is True:
        conditions.append("climbs.mountain_id IS NOT NULL")
    elif climbed is False:
        conditions.append("climbs.mountain_id IS NULL")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    sort_options = {
        "name": "mountains.name",
        "height": "mountains.height"
    }
    sort_column = sort_options.get(
        sort_by,
        "mountains.name"
    )
    direction = "DESC" if descending else "ASC"
    query += f" ORDER BY {sort_column} {direction}"
    cursor.execute(query, parameters)
    return cursor.fetchall()

def get_classifications():
    cursor.execute("""
        SELECT classification
        FROM classifications
        ORDER BY classification
    """)
    return [row[0] for row in cursor.fetchall()]

def get_statistics():
    query = """
        SELECT
            classifications.classification,
            COUNT(DISTINCT mountain_classifications.mountain_id),
            COUNT(DISTINCT climbs.mountain_id)
        FROM classifications
        JOIN mountain_classifications
            ON classifications.id = mountain_classifications.classification_id
        LEFT JOIN climbs
            ON mountain_classifications.mountain_id = climbs.mountain_id
        GROUP BY classifications.classification
    """

    cursor.execute(query)
    return cursor.fetchall()

def get_mountain_list():
    cursor.execute("""
        SELECT *
        FROM mountains
    """)
    return cursor.fetchall()

def delete_climb(climb_id):
    query = """
        DELETE FROM climbs
        WHERE id = ?
    """
    cursor.execute(query, (climb_id,))
    conn.commit()

def haversine(lat1,lon1,lat2,lon2):
    r = 6378*1000                           #radius of earth in m
    dlat = (lat1-lat2)*math.pi/180          #delta angle of latitude in radians
    dlon = (lon1-lon2)*math.pi/180          #delta angle of longitude in radians
    a = math.sin(dlat/2)**2 + math.cos(lat1*math.pi/180) * math.cos(lat2*math.pi/180) * math.sin(dlon/2)**2
    c = 2* math.atan2(math.sqrt(a),math.sqrt(1-a))
    d = r*c
    return d

def bearing(lat1,lon1,lat2,lon2):       #lat2,lon2 = mountain
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    d_lon = math.radians(lon2-lon1)
    x = math.sin(d_lon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(d_lon))
    initial_bearing_rad = math.atan2(x, y)
    initial_bearing_deg = math.degrees(initial_bearing_rad)
    compass_bearing = (initial_bearing_deg + 360) % 360
    directions = [
        "N", "NNE", "NE", "ENE", 
        "E", "ESE", "SE", "SSE", 
        "S", "SSW", "SW", "WSW", 
        "W", "WNW", "NW", "NNW"
    ]
    index = int((compass_bearing + 11.25) % 360 / 22.5)
    return directions[index]

def class_name(name):
    return classification_display_names.get(name,name)

def main():
    global conn, cursor
    app = HikingApp()
    db_path = os.path.join(app.user_data_dir, "mountains.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    create_tables()
    app.run() 

if __name__== "__main__":
    main() 
