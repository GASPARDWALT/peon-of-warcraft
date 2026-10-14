"""Read-only input readiness for ordinary Peon battle validators."""


class OrdinaryBattleReadiness:
    """Observe the actual main-menu input loop, not its earlier draw call.

    The inherited generic StaticMenuJoypad hook retains the battle context
    across native move-result text. That can advertise an actionable menu
    while the LCD still waits for an A press to finish the result message.
    """

    def open(self):
        self.main_input_entries = 0
        super().open()
        self.p.hook_register(*self.sym["_StaticMenuJoypad"], self.main_input, None)
        self.p.hook_register(*self.sym["DoTurn"], self.action_input, None)
        self.p.hook_deregister(*self.sym["MoveSelectionScreen"])
        self.p.hook_register(*self.sym["MoveSelectionScreen"], self.move_input, None)

    def battle_menu(self, _):
        self.phase, self.context = "battle_drawing", None
        self.menus += 1

    def static_ready(self, _):
        # The later native input hook below owns battle readiness.
        if self.context and self.context != "battle":
            self.phase = self.context

    def main_input(self, _):
        strings = int.from_bytes(bytes(self.read("wMenuData_2DMenuItemStringsAddr", 2)), "little")
        if self.read("wBattleMode")[0] and strings == self.sym["BattleMenuHeader.Text"][1]:
            self.phase, self.context = "battle", None
            self.main_input_entries += 1
            self.p.button_release("a")
            self.p.button_release("b")

    def action_input(self, _):
        self.phase, self.context = "action", None

    def move_input(self, _):
        self.move_menus += 1
        self.phase, self.context = "moves", None

    def ready(self, phase):
        if phase == "battle":
            self.wait_for(lambda: self.phase == "battle" or not self.read("wBattleMode")[0], True)
            self.p.button_release("a")
            self.p.button_release("b")
            self.p.tick(8, True)
        else:
            super().ready(phase)
