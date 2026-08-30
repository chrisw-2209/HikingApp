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